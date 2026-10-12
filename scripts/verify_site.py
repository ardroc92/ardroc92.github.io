#!/usr/bin/env python3
"""Verify the static migration against its captured content, without network access.

Run ``python3 scripts/verify_site.py`` from any directory. The verification report
is written to migration/verification-report.json; any discrepancy exits with 1.
Only whitespace, local URL rewriting, Algorithms tabs, obsolete YouTube embed
parameters, and the requested thumbnail/watch-link fallback may differ.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


VOID = set("area base br col embed hr img input link meta param source track wbr".split())
TABS = ("home", "syllabus", "calendar", "lecturematerial", "hw", "exams", "staff")
TAB_LABELS = dict(zip(TABS, ("Home", "Syllabus", "Calendar", "Lecture & Section Material", "Assignments", "Exams", "Course Staff")))
OWN_HOSTS = {"andreacoladangelo.com", "www.andreacoladangelo.com"}


def compact(value):
    """Compare visible content verbatim, permitting only whitespace differences."""
    return re.sub(r"\s+", "", value)


class Node:
    def __init__(self, tag="document", attrs=(), parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []

    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.nodes()

    def text(self):
        if self.tag in {"script", "style"}:
            return ""
        return "".join(child.text() if isinstance(child, Node) else child for child in self.children)

    def inside(self, other):
        node = self
        while node:
            if node is other:
                return True
            node = node.parent
        return False


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.current = self.root
        self.feed(content)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        node = self.current
        while node.parent:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.current.children.append(data)

    def nodes(self):
        return self.root.nodes()

    def by_id(self, value):
        return next((n for n in self.nodes() if n.attrs.get("id") == value), None)

    def is_redirect(self):
        return any(n.tag == "meta" and n.attrs.get("http-equiv", "").lower() == "refresh" for n in self.nodes())


class Verifier:
    def __init__(self, root):
        self.root = root
        self.baseline = json.loads((root / "migration/content-baseline.json").read_text())
        self.pages = self.baseline["pages"]
        self.file_to_source = {(root / p["file"]).resolve(): p["original_path"] for p in self.pages}
        self.file_to_source[(root / "home/index.html").resolve()] = "/home"
        self.documents = {}
        self.issues = []
        self.page_results = []
        self.local_references = 0

    def issue(self, category, path, message, **detail):
        self.issues.append(dict(category=category, path=str(path), message=message, **detail))

    def read(self, path):
        path = path.resolve()
        if path not in self.documents:
            self.documents[path] = Document(path.read_text(encoding="utf-8"))
        return self.documents[path]

    def local_target(self, href, file):
        url = urlsplit(href)
        if url.scheme or url.netloc:
            return None
        path = unquote(url.path)
        target = (self.root / path.lstrip("/")) if path.startswith("/") else (file.parent / path if path else file)
        target = target.resolve()
        if target.is_dir():
            target /= "index.html"
        return target, unquote(url.fragment)

    def destination(self, href, file=None):
        url = urlsplit(href)
        if url.hostname in OWN_HOSTS:
            path = url.path.rstrip("/") or "/home"
            return "site:" + path + ("#" + url.fragment if url.fragment else "")
        if url.hostname == "sites.google.com" and url.path.startswith("/view/andrea-coladangelo/"):
            path = url.path.removeprefix("/view/andrea-coladangelo").rstrip("/") or "/home"
            return "site:" + path + ("#" + url.fragment if url.fragment else "")
        if url.scheme or url.netloc:
            return href  # External URLs must retain every original character.
        if file is None:
            path = url.path.rstrip("/") or "/home"
            return "site:" + path + ("#" + url.fragment if url.fragment else "")
        target, fragment = self.local_target(href, file)
        source = self.file_to_source.get(target)
        if source:
            if re.fullmatch(r"/teaching/cse421au(?:25|26)", source) and fragment in TABS:
                source += "" if fragment == "home" else "/" + fragment
                fragment = ""
            return "site:" + source + ("#" + fragment if fragment else "")
        return "local:" + target.as_posix() + ("#" + fragment if fragment else "")

    @staticmethod
    def source_blocks(scope):
        return [n for n in scope.nodes() if "data-source-block" in n.attrs and compact(n.text())]

    def scopes(self, page):
        """Return document, file, text blocks and content scopes for a source page."""
        match = re.fullmatch(r"(/teaching/cse421au(?:25|26))(?:/(\w+))?", page["original_path"])
        if match:
            course, tab = match.group(1), match.group(2) or "home"
            parent_file = self.root / course.lstrip("/") / "index.html"
            if parent_file.exists():
                doc = self.read(parent_file)
                panels = [doc.by_id(name) for name in TABS]
                if all(panels):
                    panel = doc.by_id(tab)
                    shared = [n for n in self.source_blocks(doc.root) if not any(n.inside(p) for p in panels)]
                    return doc, parent_file, shared + self.source_blocks(panel), shared + [panel], True, tab
        file = self.root / page["file"]
        doc = self.read(file)
        main = next((n for n in doc.nodes() if n.tag == "main"), doc.root)
        return doc, file, self.source_blocks(main), [main], False, None

    @staticmethod
    def all_nodes(scopes):
        seen = set()
        for scope in scopes:
            for node in scope.nodes():
                if id(node) not in seen:
                    seen.add(id(node))
                    yield node

    def verify_page(self, page):
        original = page["original_path"]
        before = len(self.issues)
        try:
            doc, file, blocks, scopes, tabbed, tab = self.scopes(page)
        except (OSError, ValueError) as error:
            self.issue("page", original, str(error))
            return
        expected = [compact(text) for text in page["source_blocks"] if compact(text)]
        actual = [compact(n.text()) for n in blocks]
        if expected != actual:
            differences = [{"block": i, "expected": expected[i] if i < len(expected) else None,
                            "actual": actual[i] if i < len(actual) else None}
                           for i in range(max(len(expected), len(actual)))
                           if (expected[i] if i < len(expected) else None) != (actual[i] if i < len(actual) else None)]
            self.issue("text", original, "Source text blocks differ beyond whitespace", differences=differences)

        nodes = list(self.all_nodes(scopes))
        expected_links = Counter((compact(link["text"]), self.destination(link["href"])) for link in page["links"])
        if original == "/other":
            # Requested playback fix: retain the video and add a direct-watch fallback.
            expected_links[(compact("▶Watch on YouTube"), "https://www.youtube.com/watch?v=B7gJs7cUL24")] += 1
        actual_links = Counter((compact(n.text()), self.destination(n.attrs["href"], file)) for n in nodes if n.tag == "a" and "href" in n.attrs)
        if tabbed and "/cse421au26" in original:
            # Google Sites left the active tab unlinked. All tabs are actionable now.
            expected_links[(compact(TAB_LABELS[tab]), "site:" + original)] += 1
        missing, extra = expected_links - actual_links, actual_links - expected_links
        if missing or extra:
            fmt = lambda counter: [{"text": key[0], "destination": key[1], "count": count} for key, count in counter.items()]
            self.issue("links", original, "Content link labels or destinations differ", missing=fmt(missing), extra=fmt(extra))

        expected_images = Counter((self.root / image["local"]).resolve().as_posix() for image in page["images"])
        if original == "/other":
            # Requested thumbnail for direct file previews and the no-JS fallback.
            expected_images[(self.root / "assets/images/music-video-thumbnail.jpg").resolve().as_posix()] += 1
        actual_images = Counter()
        for node in nodes:
            if node.tag == "img":
                src = node.attrs.get("src", "")
                target = self.local_target(src, file)
                actual_images[target[0].as_posix() if target else src] += 1
        if expected_images != actual_images:
            self.issue("images", original, "Images differ from their original-to-local mapping", missing=dict(expected_images - actual_images), extra=dict(actual_images - expected_images))

        for embed in page["embeds"]:
            if embed["kind"] == "iframe":
                source = urlsplit(embed["src"])
                candidates = [n.attrs.get("src", "") for n in nodes if n.tag == "iframe"]
                if source.hostname in {"www.youtube.com", "youtube.com"}:
                    matches = [src for src in candidates if urlsplit(src).hostname in {"www.youtube.com", "youtube.com"} and urlsplit(src).path == source.path]
                else:
                    matches = [src for src in candidates if src == embed["src"]]
                if not matches:
                    self.issue("embed", original, "Original iframe is missing", expected=embed["src"], actual=candidates)
            elif embed["kind"] == "html":
                embedded = Document(embed["code"])
                expected_scripts = [n.attrs["src"] for n in embedded.nodes() if n.tag == "script" and "src" in n.attrs]
                expected_apps = [c for n in embedded.nodes() for c in n.attrs.get("class", "").split() if c.startswith("elfsight-app-")]
                actual_scripts = [n.attrs.get("src") for n in nodes if n.tag == "script"]
                actual_classes = {c for n in nodes for c in n.attrs.get("class", "").split()}
                if any(src not in actual_scripts for src in expected_scripts) or any(c not in actual_classes for c in expected_apps):
                    self.issue("embed", original, "Embedded HTML script or application identifier is missing", scripts=expected_scripts, applications=expected_apps)
        self.page_results.append(dict(source_path=original, file=file.relative_to(self.root).as_posix(), panel=tab if tabbed else None,
                                      text_blocks=len(expected), links=sum(expected_links.values()), images=sum(expected_images.values()),
                                      passed=len(self.issues) == before))

    def verify_documents(self):
        for file in sorted(self.root.rglob("*.html")):
            if any(p.startswith(".") for p in file.relative_to(self.root).parts):
                continue
            doc = self.read(file)
            relative = file.relative_to(self.root).as_posix()
            nodes = list(doc.nodes())
            ids = Counter(n.attrs["id"] for n in nodes if "id" in n.attrs)
            duplicates = {key: count for key, count in ids.items() if count > 1}
            if duplicates:
                self.issue("ids", relative, "Duplicate element ids", duplicates=duplicates)
            h1_count = sum(n.tag == "h1" for n in nodes)
            if not doc.is_redirect() and h1_count != 1:
                self.issue("heading", relative, "Nonredirect documents require exactly one h1", count=h1_count)
            for node in nodes:
                if node.tag == "img":
                    if "alt" not in node.attrs:
                        self.issue("accessibility", relative, "Image is missing an alt attribute", src=node.attrs.get("src"))
                    src = node.attrs.get("src", "")
                    host = urlsplit(src).hostname or ""
                    if "google" in host or "gstatic" in host:
                        self.issue("images", relative, "Image still depends on Google hosting", src=src)
                for attribute in ("href", "src"):
                    if attribute not in node.attrs:
                        continue
                    value = node.attrs[attribute]
                    target = self.local_target(value, file)
                    if target is None:
                        continue
                    self.local_references += 1
                    target_file, fragment = target
                    if not target_file.exists():
                        self.issue("local-reference", relative, "Local href/src target does not exist", attribute=attribute, value=value)
                    elif fragment and target_file.suffix.lower() == ".html" and not fragment.startswith(":~:text="):
                        if self.read(target_file).by_id(fragment) is None:
                            self.issue("fragment", relative, "Local fragment has no target id", value=value)

    def run(self):
        for page in self.pages:
            self.verify_page(page)
        self.verify_documents()
        return dict(verified_at=datetime.now(timezone.utc).isoformat(), source=self.baseline["source"],
                    passed=not self.issues, source_pages=len(self.pages), html_documents=len(self.documents),
                    local_references_checked=self.local_references, pages=self.page_results, issues=self.issues)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path, help="Optional report destination (default: migration/verification-report.json)")
    args = parser.parse_args()
    root = args.root.resolve()
    report = Verifier(root).run()
    destination = args.report or root / "migration/verification-report.json"
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {report['source_pages']} source pages, "
          f"{report['html_documents']} HTML documents, {report['local_references_checked']} local references")
    for issue in report["issues"]:
        print(f"  [{issue['category']}] {issue['path']}: {issue['message']}")
    print(f"Report: {destination}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

# Andrea Coladangelo’s website

A plain HTML, CSS, and JavaScript migration of https://www.andreacoladangelo.com, captured on October 12, 2026. No build step, package manager, or framework is required.

The migration includes the content of 29 public source pages. The two Algorithms courses each combine their seven original pages into one page with tabs. Their old subpage URLs remain as redirects. The public but unlisted Talks page is also included, with its original absence from the main menu preserved.

## Preview and edit

Open `index.html` in your browser, or serve this folder locally:

```sh
python3 -m http.server 8000
```

Then visit http://localhost:8000. Stop the server with Ctrl+C. Use this HTTP preview to play the embedded YouTube video: YouTube requires an HTTP referrer and rejects direct `file://` embeds. When opening the HTML directly, the Music section shows the video thumbnail with a play button that opens YouTube. The embedded player is available on GitHub Pages.

Edit each page’s HTML directly. For example:

- `index.html` — homepage, biography, news, selected publications, and service.
- `publications/index.html` — complete publication list.
- `teaching/index.html` — course directory.
- `teaching/cse434sp26/index.html` — Spring 2026 quantum computation.
- `teaching/cse421au26/index.html` — all Autumn 2026 Algorithms content, organized into seven tab panels.
- `teaching/cse421au25/index.html` — all Autumn 2025 Algorithms content.
- `advising/index.html`, `other/index.html`, `talks/index.html` — remaining personal pages.
- `assets/site.css` — shared appearance and responsive layouts.
- `assets/course-tabs.js` — tab interaction and bookmark/history handling.
- `assets/images/` — local copies of all images.

In Algorithms HTML, edit the panel with the corresponding ID: `home`, `syllabus`, `calendar`, `lecturematerial`, `hw`, `exams`, or `staff`. Each tab can be bookmarked, for example `teaching/cse421au26/index.html#syllabus`. With JavaScript disabled, all panels remain readable on one page.

Directory-based pages retain the original URL structure: `/teaching/cse434sp26` resolves to the course’s `index.html`. Internal links use relative paths, so the site also works under a GitHub project repository’s subdirectory. `/home/` redirects to the homepage.

## Publish on GitHub Pages

1. Create a GitHub repository and upload this folder’s contents to its root, including `.nojekyll`.
2. In the repository, open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, select your branch (usually `main`) and **/(root)**, and save.
4. Use the URL GitHub reports when deployment completes.

A repository named `YOUR-USERNAME.github.io` gives an account-level site; an ordinary repository also works. There is no build command to configure. See [GitHub’s publishing-source instructions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

To move `andreacoladangelo.com`, first configure the custom domain in GitHub Pages, then update your DNS using [GitHub’s custom-domain instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site). GitHub creates a `CNAME` file when using branch publishing. This folder does not change DNS or the currently published Google Site.

## Content preservation and checks

The original wording, including dated announcements and course policies, is retained. Styling, navigation markup, paragraph spacing, and headings were cleaned up. Google Sites’ search, branding, and report-abuse interface are hosting controls and were not copied.

External resources retain their original links, including Google Drive, Docs/Slides, arXiv, and course platforms. These resources are linked rather than downloaded; they keep their existing access permissions and depend on their original hosts. The music video and 2025 Elfsight calendar remain third-party embeds. The YouTube video ID is retained, with Google Sites’ temporary embedding parameters removed. The 2026 calendar image is stored locally.

`migration/content-baseline.json` records every captured page’s original text, links, images, and embeds. `migration/assets.json` records image sources, local paths, dimensions, and checksums. `migration/source-snapshot.zip` contains the original public HTML for reference. These migration records are not required to serve the site.

Run the offline verification with Python 3:

```sh
python3 scripts/verify_site.py
```

It checks text against the captured baseline, link destinations, local assets and paths, and page structure. Once you intentionally edit content, a baseline mismatch is expected; the baseline is an archival record, not a source that regenerates the website.

The source Google Site does not provide a usable public sitemap. Discovery followed every internal link from the homepage and checked search results for additional pages; this found Talks. Any unpublished or undiscoverable unlinked page would require its URL or a Google Sites export.

/* Course content remains fully available when JavaScript is unavailable. */
(() => {
  'use strict';

  const tablist = document.querySelector('.course-nav[role="tablist"]');
  if (!tablist) return;

  const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
  const panels = tabs.map(tab => document.getElementById(tab.getAttribute('aria-controls')));
  if (!tabs.length || panels.some(panel => !panel)) return;

  function targetFromHash(hash) {
    let id;
    try {
      id = decodeURIComponent(hash.replace(/^#/, ''));
    } catch {
      return null;
    }
    return id ? document.getElementById(id) : null;
  }

  function panelForTarget(target) {
    const panel = target && target.closest('.course-panel');
    return panels.includes(panel) ? panel : null;
  }

  function selectPanel(panel, focusTab = false) {
    panels.forEach((candidate, index) => {
      const selected = candidate === panel;
      candidate.hidden = !selected;
      tabs[index].setAttribute('aria-selected', String(selected));
      tabs[index].tabIndex = selected ? 0 : -1;
      if (selected && focusTab) tabs[index].focus({ preventScroll: true });
    });
  }

  function updateAddress(hash, replace = false) {
    if (location.hash === hash) return;
    const destination = new URL(location.href);
    destination.hash = hash;
    history[replace ? 'replaceState' : 'pushState'](null, '', destination);
  }

  function followAddress() {
    const target = targetFromHash(location.hash);
    const panel = panelForTarget(target) || panels[0];
    selectPanel(panel);
    // Old Google Sites heading fragments still open and reveal their section.
    if (target && panelForTarget(target)) {
      requestAnimationFrame(() => target.scrollIntoView({ block: 'start' }));
    }
  }

  tablist.addEventListener('keydown', event => {
    const current = tabs.indexOf(event.target);
    if (current < 0 || event.altKey || event.ctrlKey || event.metaKey) return;
    let next;
    switch (event.key) {
      case 'ArrowRight': next = (current + 1) % tabs.length; break;
      case 'ArrowLeft': next = (current + tabs.length - 1) % tabs.length; break;
      case 'Home': next = 0; break;
      case 'End': next = tabs.length - 1; break;
      case ' ': next = current; break;
      default: return;
    }
    event.preventDefault();
    selectPanel(panels[next], true);
    // Arrow-key exploration should not add a history entry for every tab.
    updateAddress('#' + panels[next].id, true);
  });

  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.altKey ||
        event.ctrlKey || event.metaKey || event.shiftKey) return;
    const link = event.target.closest('a[href]');
    if (!link || link.hasAttribute('download') ||
        (link.target && link.target !== '_self')) return;
    const destination = new URL(link.href, location.href);
    if (destination.origin !== location.origin ||
        destination.pathname !== location.pathname ||
        destination.search !== location.search) return;
    const target = targetFromHash(destination.hash);
    const panel = panelForTarget(target);
    if (!panel) return;

    event.preventDefault();
    const isTab = tabs.includes(link);
    selectPanel(panel, isTab);
    updateAddress(destination.hash);
    if (!isTab) {
      panel.focus({ preventScroll: true });
      target.scrollIntoView({ block: 'start' });
    }
  });

  window.addEventListener('hashchange', followAddress);
  window.addEventListener('popstate', followAddress);
  document.documentElement.classList.add('course-tabs-enhanced');
  followAddress();
})();

/* YouTube requires an HTTP referrer. Direct file previews use the watch link. */
(() => {
  'use strict';

  if (!['http:', 'https:'].includes(location.protocol)) return;

  document.querySelectorAll('[data-video-player]').forEach(player => {
    const template = player.querySelector('[data-video-embed]');
    const mount = player.querySelector('[data-video-mount]');
    if (!template || !mount) return;

    mount.append(template.content.cloneNode(true));
    player.classList.add('is-embedded');
  });
})();

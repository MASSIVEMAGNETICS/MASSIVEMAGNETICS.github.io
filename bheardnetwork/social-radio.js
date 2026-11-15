'use strict';
/* social-radio.js — B Heard Radio 24/7 page wiring (radio slice).
 *
 * Reuses the single existing #player / #audio / #nowplaying elements
 * and the shared app.js globals ($, esc, api). Nothing in this file
 * redefines them, and it does not touch app.js / index.html / style.css
 * (the section markup + this script tag are the coordinator's merge).
 *
 * The radio is a shared live stream, not a track: pressing "Listen
 * live" points the one global player at /radio/stream (same-origin
 * proxy to the streamer, so the board's CSP media-src 'self' holds)
 * and the now-playing line refreshes from /api/radio/now every 30s.
 * Pressing a track play button stops the radio -- one player, one
 * sound at a time, exactly like the rest of the board.
 *
 * On the static Pages copy the shim (bheard-api.js) resolves
 * '/radio/stream' to the live base or a demo tone, so audio.src never
 * reads back as '/radio/stream' there. The play listener therefore
 * also accepts the shim's marker: the shim sets
 * audio.dataset.radioStream = '1' when it maps a radio src and clears
 * it for any other src. No marker + no '/radio/stream' in the src
 * means a track was played, and the radio stops.
 *
 * No inline handlers, no external URLs, all user text through esc().
 */
(function () {
  var timer = null;
  var playing = false;

  function els() {
    return {
      now: $('#radio-now'),
      next: $('#radio-next'),
      listeners: $('#radio-listeners'),
      btn: $('#radio-play'),
      audio: $('#audio'),
      player: $('#player'),
      nowPlaying: $('#nowplaying')
    };
  }

  function render(d) {
    var e = els();
    if (!e.now) return;
    if (!d || !d.on_air) {
      e.now.textContent = 'Radio is off air right now — check back soon.';
      if (e.next) e.next.textContent = '';
      if (e.listeners) e.listeners.textContent = '';
      return;
    }
    var t = d.track || {};
    var line = 'ON AIR: ' + (t.title || 'B Heard Radio');
    if (t.artist) line += ' — ' + t.artist;
    e.now.textContent = line;
    if (e.next) {
      var up = (d.up_next || []).slice(0, 3).map(function (x) {
        return x.title + (x.artist ? ' — ' + x.artist : '');
      });
      e.next.textContent = up.length ? 'Up next: ' + up.join(' · ') : '';
    }
    if (e.listeners) {
      e.listeners.textContent = (typeof d.listeners === 'number')
        ? d.listeners + (d.listeners === 1 ? ' listener' : ' listeners')
          + ' tuned in' : '';
    }
    if (playing && e.nowPlaying) {
      e.nowPlaying.textContent = line;
    }
  }

  function refresh() {
    api('radio/now').then(render).catch(function () {
      render({ on_air: false });
    });
  }

  function toggleRadio() {
    var e = els();
    if (!e.audio) return;
    if (playing) {
      e.audio.pause();
      playing = false;
      if (e.btn) e.btn.textContent = '▶ Listen live';
      return;
    }
    e.audio.src = '/radio/stream';
    e.player.hidden = false;
    e.audio.play().catch(function () {});
    playing = true;
    if (e.btn) e.btn.textContent = '⏸ Pause radio';
    refresh();
  }

  function init() {
    var e = els();
    if (!e.now || !e.btn) return;
    e.btn.addEventListener('click', toggleRadio);
    if (e.audio) {
      /* If the user plays a track, the radio stops: one player. */
      e.audio.addEventListener('play', function () {
        if (playing && e.audio.src.indexOf('/radio/stream') === -1 &&
            (!e.audio.dataset || e.audio.dataset.radioStream !== '1')) {
          playing = false;
          e.btn.textContent = '▶ Listen live';
        }
      });
    }
    refresh();
    timer = setInterval(refresh, 30000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

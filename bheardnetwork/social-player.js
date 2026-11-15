'use strict';
/* social-player.js — Slice C (music-social v2, DATA_CONTRACT section 4.3).
 *
 * Reuses the single existing #player / #audio / #nowplaying elements and
 * the shared app.js globals ($, esc, api, post, notice, me). Nothing in
 * this file redefines them.
 *
 * Play buttons use data-social-play="<trackId>". Clicking one plays that
 * track, updates #nowplaying ("title — display") and shows #player; on
 * ended, playback auto-advances to the next track in the list the button
 * came from; clicking the track that is already playing toggles pause.
 *
 * Discography: when app.js renders an artist profile into #grid, this
 * file fetches GET /api/profile/<handle>/discography and swaps the
 * track rows for discography rows (pinned track first, "Pinned" marker,
 * then newest-first, each with a play button and a vote count). The
 * profile card app.js rendered (including its Follow binding) is kept.
 *
 * Upload form: the genre select is pre-filled from the signed-in user's
 * profile genre (via GET /api/me, which slice A extends with `genre`);
 * on failure the form's existing default is left alone. After a
 * successful upload a "Post this track to the feed" action appears,
 * calling POST /api/posts {kind:"music", track_id, body:""}. The upload
 * request itself is not changed.
 *
 * No inline handlers, no external URLs, all user text through esc().
 */
(function () {
  var audio = null, player = null, nowPlaying = null;
  var queue = [];       // track objects in play order for the current list
  var queueIndex = -1;  // index of the currently playing track in queue
  var registry = new Map(); // track id -> track object (title/display)
  var renderingDiscography = false;
  var discographyHandle = null; // handle whose discography is on screen

  function els() {
    audio = $('#audio'); player = $('#player'); nowPlaying = $('#nowplaying');
    return !!audio;
  }

  function bindAudio() {
    if (!els() || audio.dataset.socialBound) return;
    audio.dataset.socialBound = '1';
    audio.addEventListener('ended', function () {
      if (queueIndex >= 0 && queueIndex + 1 < queue.length) {
        playAt(queueIndex + 1);
      } else {
        queueIndex = -1;
        markPlaying();
      }
    });
    audio.addEventListener('play', markPlaying);
    audio.addEventListener('pause', markPlaying);
  }

  function trackFromButton(btn) {
    var id = Number(btn.getAttribute('data-social-play'));
    var t = registry.get(id);
    if (!t) {
      t = {
        id: id,
        title: btn.getAttribute('data-title') || 'Untitled track',
        display: btn.getAttribute('data-display') || '',
        media_url: '/media/' + id
      };
    }
    return t;
  }

  /* The queue is the set of play buttons in the same list as the one
   * clicked (the profile grid, a feed container, or the whole document
   * as a fallback), in DOM order. */
  function listForButton(btn) {
    var scope = btn.closest('#grid') || btn.closest('[data-social-list]') || document;
    var list = [];
    scope.querySelectorAll('[data-social-play]').forEach(function (b) {
      list.push(trackFromButton(b));
    });
    return list;
  }

  function playAt(index) {
    if (!els() || index < 0 || index >= queue.length) return;
    queueIndex = index;
    var t = queue[index];
    audio.src = t.media_url || ('/media/' + t.id);
    nowPlaying.textContent = t.title + (t.display ? ' — ' + t.display : '');
    player.hidden = false;
    audio.play().catch(function () {});
    markPlaying();
  }

  function markPlaying() {
    var current = queueIndex >= 0 && queue[queueIndex] ? queue[queueIndex].id : null;
    document.querySelectorAll('[data-social-play]').forEach(function (b) {
      var isCurrent = current !== null &&
        Number(b.getAttribute('data-social-play')) === current;
      var playing = isCurrent && audio && !audio.paused;
      b.classList.toggle('playing', !!playing);
      b.setAttribute('aria-pressed', playing ? 'true' : 'false');
    });
  }

  /* Artist control (audit 2026-11-10): on your OWN discography rows you
   * get a Hide / Unhide button (POST /api/track/<id>/visibility). A
   * hidden track shows a "Hidden" marker, has no Listen button (hidden
   * tracks do not stream), and stays visible to you so you can unhide
   * it; other viewers never see it at all. */
  function discographyRow(t, pinned, own) {
    var hidden = t.status === 'hidden';
    var playBtn = hidden ? '' : '<button class="primary" data-social-play="' + t.id + '"'
      + ' data-title="' + esc(t.title) + '"'
      + ' data-display="' + esc(t.display || '') + '">\u25B6 Listen</button>';
    var visBtn = '';
    if (own) {
      visBtn = hidden
        ? '<button class="outline" data-social-visibility="' + t.id + '" data-visibility-status="published">Unhide</button>'
        : '<button class="outline" data-social-visibility="' + t.id + '" data-visibility-status="hidden">Hide</button>';
    }
    return '<article class="card discography-row">'
      + '<span class="eyebrow">' + esc(t.genre) + '</span>'
      + '<h3>' + esc(t.title)
      + (pinned ? ' <span class="eyebrow">\uD83D\uDCCC Pinned</span>' : '')
      + (hidden ? ' <span class="eyebrow">Hidden</span>' : '')
      + '</h3>'
      + '<p>' + esc(t.description || 'Independent artist release') + '</p>'
      + '<div class="row">'
      + playBtn
      + '<button class="outline" data-social-vote="' + t.id + '">\u2665 '
      + '<span class="votecount">' + Number(t.votes || 0) + '</span></button>'
      + visBtn
      + '</div></article>';
  }

  function renderDiscography(artist, tracks) {
    (tracks || []).forEach(function (t) { registry.set(t.id, t); });
    var grid = $('#grid');
    if (!grid) return;
    discographyHandle = artist && artist.handle ? artist.handle : null;
    var own = typeof me !== 'undefined' && me && artist &&
      me.handle === artist.handle;
    var pinnedId = artist && artist.pinned_track_id != null
      ? artist.pinned_track_id : null;
    var rows = (tracks || []).map(function (t) {
      return discographyRow(t, pinnedId !== null && t.id === pinnedId, own);
    }).join('');
    if (!rows) rows = '<div class="empty">No tracks published yet.</div>';
    var first = grid.querySelector('.card');
    if (first) {
      // Keep app.js's profile card (and its Follow binding); replace
      // only the track rows that follow it.
      var next;
      while ((next = first.nextSibling)) grid.removeChild(next);
      grid.insertAdjacentHTML('beforeend', rows);
    } else {
      grid.innerHTML = rows;
    }
  }

  /* Re-fetch and re-render the discography on screen (after a
   * hide/unhide toggle). Bypasses maybeRenderDiscography's guard, which
   * correctly skips re-renders while play buttons are already present. */
  function refreshDiscography() {
    if (!discographyHandle) return;
    api('profile/' + encodeURIComponent(discographyHandle) + '/discography').then(function (d) {
      renderDiscography(d.artist, d.tracks || []);
    }).catch(function (e) { notice(e.message); });
  }

  function handleFromTitle() {
    var title = $('#section-title');
    if (!title) return null;
    var m = title.textContent.match(/@([a-z0-9_]{3,24})/);
    return m ? m[1] : null;
  }

  function handleFromHash() {
    if (location.hash.indexOf('#artist/') === 0) {
      return decodeURIComponent(location.hash.slice(8));
    }
    return null;
  }

  function maybeRenderDiscography() {
    if (renderingDiscography) return;
    var grid = $('#grid');
    if (!grid || grid.querySelector('[data-social-play]')) return;
    // app.js's artist-profile render puts a Follow button in the grid;
    // slice A's enhanced card puts #social-follow-btn there instead.
    // Accept either: whichever slice renders last, this observer re-runs
    // on the grid mutation and converges on A-card + C discography rows.
    if (!grid.querySelector('#followbtn') && !grid.querySelector('#social-follow-btn')) return;
    var handle = handleFromTitle() || handleFromHash();
    if (!handle) return;
    renderingDiscography = true;
    api('profile/' + encodeURIComponent(handle) + '/discography').then(function (d) {
      renderDiscography(d.artist, d.tracks || []);
    }).catch(function (e) {
      // Route not wired yet, or the profile vanished: leave app.js's
      // own track cards in place rather than surfacing an error.
      console.warn('Discography unavailable for @' + handle, e);
    }).finally(function () { renderingDiscography = false; });
  }

  function watchGrid() {
    var grid = $('#grid');
    if (!grid || grid.dataset.socialWatched) return;
    grid.dataset.socialWatched = '1';
    new MutationObserver(function () { maybeRenderDiscography(); })
      .observe(grid, { childList: true });
    maybeRenderDiscography();
  }

  function prefillUploadGenre() {
    var sel = document.querySelector('#uploadform select[name="genre"]');
    if (!sel) return;
    function apply(genre) {
      if (!genre) return;
      var ok = Array.prototype.some.call(sel.options, function (o) {
        return o.value === genre;
      });
      if (ok) sel.value = genre;
    }
    if (typeof me !== 'undefined' && me && me.genre) { apply(me.genre); return; }
    api('me').then(function (d) {
      if (d.user && d.user.genre) apply(d.user.genre);
    }).catch(function () {});
  }

  function showPostToFeedAction() {
    if (typeof me === 'undefined' || !me) return;
    api('feed?sort=new').then(function (d) {
      var mine = (d.tracks || []).find(function (t) { return t.handle === me.handle; });
      if (!mine) return;
      var box = $('#social-post-action');
      if (!box) {
        box = document.createElement('div');
        box.id = 'social-post-action';
        box.className = 'row';
        var n = $('#notice');
        if (!n || !n.parentNode) return;
        n.parentNode.insertBefore(box, n.nextSibling);
      }
      box.replaceChildren();
      var btn = document.createElement('button');
      btn.className = 'primary';
      btn.textContent = 'Post this track to the feed';
      btn.addEventListener('click', function () {
        post('posts', { kind: 'music', track_id: mine.id, body: '' }).then(function () {
          notice('Track posted to the feed');
          box.replaceChildren();
        }).catch(function (e) { notice(e.message); });
      });
      box.append(btn);
    }).catch(function () {});
  }

  function watchUploadStatus() {
    var status = $('#uploadstatus');
    if (!status || status.dataset.socialWatched) return;
    status.dataset.socialWatched = '1';
    new MutationObserver(function () {
      if (status.textContent.trim() === 'Published!') showPostToFeedAction();
    }).observe(status, { childList: true, characterData: true, subtree: true });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-social-play]');
    if (btn) {
      if (!els()) return;
      var id = Number(btn.getAttribute('data-social-play'));
      if (queueIndex >= 0 && queue[queueIndex] && queue[queueIndex].id === id) {
        // Clicking the playing track toggles pause.
        if (audio.paused) { audio.play().catch(function () {}); }
        else { audio.pause(); }
        markPlaying();
        return;
      }
      queue = listForButton(btn);
      var idx = -1;
      queue.forEach(function (t, i) { if (t.id === id) idx = i; });
      playAt(idx < 0 ? 0 : idx);
      return;
    }
    var visBtn = e.target.closest('[data-social-visibility]');
    if (visBtn) {
      if (typeof me === 'undefined' || !me) { notice('Sign in to change visibility'); return; }
      var tid = Number(visBtn.getAttribute('data-social-visibility'));
      var st = visBtn.getAttribute('data-visibility-status');
      post('track/' + tid + '/visibility', { status: st }).then(function () {
        notice(st === 'hidden' ? 'Track hidden' : 'Track published');
        refreshDiscography();
      }).catch(function (err) { notice(err.message); });
      return;
    }
    var voteBtn = e.target.closest('[data-social-vote]');
    if (voteBtn) {
      if (typeof me === 'undefined' || !me) { notice('Sign in to vote'); return; }
      var tid = Number(voteBtn.getAttribute('data-social-vote'));
      var span = voteBtn.querySelector('.votecount');
      post('vote', { trackId: tid }).then(function (r) {
        if (span) {
          var n = Number(span.textContent) || 0;
          span.textContent = String(n + (r.voted ? 1 : -1));
        }
      }).catch(function (err) { notice(err.message); });
      return;
    }
    if (e.target.closest('#uploadbtn')) prefillUploadGenre();
  });

  window.addEventListener('hashchange', function () { maybeRenderDiscography(); });

  els();
  bindAudio();
  watchGrid();
  watchUploadStatus();
  prefillUploadGenre();

  /* Cross-slice hook for the feed (slice B): its music-post cards can
   * register their track objects here so play buttons get real
   * title/display in #nowplaying instead of the data-* fallback. */
  window.SocialPlayer = {
    renderDiscography: renderDiscography,
    registerTracks: function (list) {
      (list || []).forEach(function (t) { registry.set(t.id, t); });
    },
    playTrackById: function (id) {
      var t = registry.get(Number(id));
      queue = [t || { id: Number(id), title: 'Untitled track', display: '',
                      media_url: '/media/' + Number(id) }];
      playAt(0);
    },
    prefillUploadGenre: prefillUploadGenre,
    showPostToFeedAction: showPostToFeedAction
  };
})();

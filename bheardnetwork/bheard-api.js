'use strict';
/* B Heard Network — static-site API shim (bheard-api.js).
 *
 * Loads BEFORE app.js (see index.html script order). Two jobs:
 *
 * 1. LIVE API DETECTION. Probe, in order: ?api=<url> query param,
 *    localStorage 'bheard.apiBase', then same-origin '/api/config'.
 *    The first base that answers GET <base>/api/config with JSON wins and
 *    the page runs LIVE against the Dell API. Otherwise the page runs in
 *    DEMO mode against the in-memory demo store below. A tunnel URL is
 *    NEVER hardcoded — tunnel URLs rotate; the owner pastes the current
 *    one into the banner form and it lives only in localStorage.
 *
 *    Known limitation (live mode from GitHub Pages): the Dell API must
 *    allow cross-origin fetch from the Pages origin (CORS) for live mode
 *    to work, and the session cookie is same-origin only, so sign-in from
 *    the Pages origin needs the Dell to send CORS + credential support.
 *    Until then, live mode works when this tree is served same-origin by
 *    the Dell/tunnel, and the shim falls back to demo data otherwise.
 *
 * 2. FETCH SHIM. window.fetch is patched for '/api/...' requests only:
 *    live mode rewrites them to the detected base (and rewrites '/media/'
 *    strings inside JSON responses to absolute live URLs); demo mode
 *    answers from the demo store (seed: window.BHEARD_DEMO, demo-data.js).
 *    HTMLMediaElement.src is patched the same way so play buttons resolve
 *    '/media/<id>' to the live base or to a demo tone file.
 *
 * Demo sign-in is local-only: any demo account email, any password,
 * nothing leaves the browser. Demo writes (votes, follows, posts,
 * comments, uploads, profile edits) mutate the in-memory demo store.
 */
(function () {
  var DEMO = window.BHEARD_DEMO || null;
  var LS_KEY = 'bheard.apiBase';
  var SESSION_KEY = 'bheard.demoSession';
  var PROBE_MS = 2500;
  var nativeFetch = window.fetch.bind(window);
  var state = { mode: 'pending', apiBase: null, config: null };
  var GENRES = ['Hip-Hop', 'Rock', 'Pop', 'R&B', 'Electronic', 'Country', 'Other'];
  var HANDLE_RE = /^[a-z0-9_]{3,24}$/;
  var HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;

  /* ------------------------------------------------------------------ */
  /* Small helpers                                                       */
  /* ------------------------------------------------------------------ */
  function $(s) { return document.querySelector(s); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function clone(v) { return JSON.parse(JSON.stringify(v)); }
  function storeGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function storeSet(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
  function storeDel(k) { try { window.localStorage.removeItem(k); } catch (e) { /* private mode */ } }
  function toneFor(trackId) { return 'demo-media/' + ((((Number(trackId) - 1) % 4) + 4) % 4 + 1) + '.wav'; }
  function withTimeout(promise, ms) {
    return Promise.race([promise, new Promise(function (_, reject) {
      setTimeout(function () { reject(new Error('probe timeout')); }, ms);
    })]);
  }

  /* ------------------------------------------------------------------ */
  /* Live API detection                                                  */
  /* ------------------------------------------------------------------ */
  function candidates() {
    var list = [];
    var q = null;
    try { q = new URLSearchParams(window.location.search).get('api'); } catch (e) { q = null; }
    if (q && /^https?:\/\//.test(q)) list.push(q.replace(/\/+$/, ''));
    var stored = storeGet(LS_KEY);
    if (stored && /^https?:\/\//.test(stored)) list.push(stored.replace(/\/+$/, ''));
    list.push(''); // same-origin last
    return list.filter(function (v, i, a) { return a.indexOf(v) === i; });
  }

  async function probe(base) {
    try {
      var r = await withTimeout(nativeFetch((base || '') + '/api/config', { credentials: 'same-origin' }), PROBE_MS);
      if (!r.ok) return null;
      var d = await r.json();
      if (!d || typeof d !== 'object') return null;
      return d;
    } catch (e) { return null; }
  }

  var ready = (async function detect() {
    var bases = candidates();
    for (var i = 0; i < bases.length; i++) {
      var config = await probe(bases[i]);
      if (config) {
        state.mode = 'live';
        state.apiBase = bases[i];
        state.config = config;
        updateBanner();
        return state;
      }
    }
    state.mode = 'demo';
    state.apiBase = null;
    state.config = { googleClientId: null };
    updateBanner();
    return state;
  })();
  window.BHEARD_READY = ready;

  function updateBanner() {
    var banner = $('#bheard-banner');
    var modeEl = $('#bheard-mode');
    var textEl = $('#bheard-mode-text');
    var input = $('#bheard-api-input');
    if (!banner || !modeEl || !textEl) return;
    if (state.mode === 'live') {
      banner.classList.add('live');
      modeEl.textContent = '● LIVE';
      var host = state.apiBase ? state.apiBase.replace(/^https?:\/\//, '') : 'same origin';
      textEl.textContent = 'Connected to the live B Heard Network (' + host + '). Demo data is off — artists, tracks and posts are real.';
    } else {
      banner.classList.remove('live');
      modeEl.textContent = 'DEMO MODE';
    }
    if (input && state.apiBase) input.value = state.apiBase;
  }

  /* ------------------------------------------------------------------ */
  /* Live fetch: rewrite /api + /media to the detected base              */
  /* ------------------------------------------------------------------ */
  function rewriteMediaStrings(value, base) {
    if (typeof value === 'string') {
      return value.indexOf('/media/') === 0 ? base + value : value;
    }
    if (Array.isArray(value)) return value.map(function (v) { return rewriteMediaStrings(v, base); });
    if (value && typeof value === 'object') {
      var out = {};
      Object.keys(value).forEach(function (k) { out[k] = rewriteMediaStrings(value[k], base); });
      return out;
    }
    return value;
  }

  async function liveFetch(input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    var target = state.apiBase ? state.apiBase + url : url;
    var r = await nativeFetch(target, init);
    var type = (r.headers.get('content-type') || '').toLowerCase();
    if (state.apiBase && type.indexOf('application/json') >= 0) {
      var text = await r.text();
      try {
        var data = rewriteMediaStrings(JSON.parse(text), state.apiBase);
        return new Response(JSON.stringify(data), { status: r.status, headers: { 'Content-Type': 'application/json' } });
      } catch (e) { return new Response(text, { status: r.status, headers: { 'Content-Type': 'application/json' } }); }
    }
    return r;
  }

  function resolveMediaSrc(v) {
    if (typeof v !== 'string') return v;
    if (v === '/radio/stream') {
      /* Live: the real stream at the detected base. Demo: the current
       * demo radio track's tone (the demo playlist loops). */
      if (state.mode === 'live') return (state.apiBase || '') + v;
      var cur = demoRadioCurrent();
      return cur ? toneFor(cur.id) : v;
    }
    if (v.indexOf('/media/') !== 0) return v;
    if (state.mode === 'live') return (state.apiBase || '') + v;
    var id = v.split('/').pop();
    return toneFor(id);
  }

  /* Patch <audio> src assignment (app.js / social-player.js set
   * audio.src = '/media/<id>'). Assignments made before detection
   * finishes resolve as demo tones; play clicks happen after load. */
  (function patchMediaSrc() {
    if (!window.HTMLMediaElement) return;
    var desc = Object.getOwnPropertyDescriptor(window.HTMLMediaElement.prototype, 'src');
    if (!desc || !desc.set) return;
    Object.defineProperty(window.HTMLMediaElement.prototype, 'src', {
      get: desc.get,
      set: function (v) {
        /* Marker contract with social-radio.js: its play listener must
         * not mistake a resolved radio src for a track play. The marker
         * is set only for '/radio/stream' assignments and cleared for
         * anything else, so a track play always stops the radio and a
         * radio (re)play never does. */
        if (this.dataset) {
          if (v === '/radio/stream') this.dataset.radioStream = '1';
          else delete this.dataset.radioStream;
        }
        desc.set.call(this, resolveMediaSrc(v));
      },
      configurable: true
    });
  })();

  /* ------------------------------------------------------------------ */
  /* Demo store (in-memory; seeded from window.BHEARD_DEMO)             */
  /* ------------------------------------------------------------------ */
  var demo = null;
  function demoStore() {
    if (demo) return demo;
    var seed = clone(DEMO || { users: [], tracks: [], posts: [], comments: [], post_likes: [], votes: [], follows: [] });
    var sessionHandle = storeGet(SESSION_KEY);
    demo = {
      users: seed.users, tracks: seed.tracks, posts: seed.posts,
      comments: seed.comments,
      postLikes: new Set((seed.post_likes || []).map(function (x) { return x.user_id + ':' + x.post_id; })),
      votes: new Set((seed.votes || []).map(function (x) { return x.user_id + ':' + x.track_id; })),
      follows: new Set((seed.follows || []).map(function (x) { return x.follower + ':' + x.followed; })),
      session: null,
      nextPostId: 1 + Math.max.apply(null, seed.posts.map(function (p) { return p.id; }).concat([0])),
      nextCommentId: 1 + Math.max.apply(null, seed.comments.map(function (c) { return c.id; }).concat([0])),
      nextTrackId: 1 + Math.max.apply(null, seed.tracks.map(function (t) { return t.id; }).concat([0])),
      nextUserId: 1 + Math.max.apply(null, seed.users.map(function (u) { return u.id; }).concat([0]))
    };
    if (sessionHandle) {
      demo.session = demo.users.find(function (u) { return u.handle === sessionHandle; }) || null;
    }
    return demo;
  }

  function demoUserByHandle(handle) { return demoStore().users.find(function (u) { return u.handle === handle; }) || null; }
  function demoUserById(id) { return demoStore().users.find(function (u) { return u.id === id; }) || null; }
  function demoTrackById(id) { return demoStore().tracks.find(function (t) { return t.id === id; }) || null; }
  function nowEpoch() { return Math.floor(Date.now() / 1000); }

  function publicProfile(user) {
    var d = demoStore();
    var published = d.tracks.filter(function (t) { return t.user_id === user.id && t.status === 'published'; });
    var pinned = null;
    if (user.pinned_track_id) {
      var pt = demoTrackById(user.pinned_track_id);
      if (pt && pt.status === 'published') pinned = trackJson(pt);
    }
    return {
      id: user.id, handle: user.handle, display: user.display, bio: user.bio || '',
      role: user.role, plan: user.plan,
      avatar_url: user.avatar_url || null, banner_url: user.banner_url || null,
      genre: user.genre || 'Other', location: user.location || '',
      website: user.website || '', links: user.links || [],
      theme: user.theme || {}, pinned_track_id: user.pinned_track_id || null,
      pinned_track: pinned,
      followers_count: Array.from(d.follows).filter(function (k) { return Number(k.split(':')[1]) === user.id; }).length,
      following_count: Array.from(d.follows).filter(function (k) { return Number(k.split(':')[0]) === user.id; }).length,
      track_count: published.length
    };
  }

  function trackJson(t) {
    var u = demoUserById(t.user_id) || { handle: 'demo_unknown', display: 'Demo artist' };
    return {
      id: t.id, title: t.title, genre: t.genre, description: t.description || '',
      created: t.created, votes: t.votes || 0, status: t.status || 'published',
      media_url: toneFor(t.id), handle: u.handle, display: u.display
    };
  }

  function postJson(p, viewerId) {
    var d = demoStore();
    var author = demoUserById(p.author_id) || { id: 0, handle: 'demo_unknown', display: 'Demo artist', avatar_url: null };
    var track = null;
    if (p.track_id) {
      var t = demoTrackById(p.track_id);
      if (t) track = trackJson(t);
    }
    return {
      id: p.id, kind: p.kind, body: p.body || '',
      created_at: p.created, updated_at: p.updated_at,
      author: { id: author.id, handle: author.handle, display: author.display, avatar_url: author.avatar_url || null },
      track: track,
      like_count: Array.from(d.postLikes).filter(function (k) { return Number(k.split(':')[1]) === p.id; }).length,
      comment_count: d.comments.filter(function (c) { return c.post_id === p.id && c.status === 'published'; }).length,
      liked_by_me: viewerId ? d.postLikes.has(viewerId + ':' + p.id) : false
    };
  }

  function jsonResponse(body, status) {
    return new Response(JSON.stringify(body), {
      status: status || 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }
  function demoError(message, status) { return jsonResponse({ error: message }, status || 400); }
  function requireSession() {
    var d = demoStore();
    if (!d.session) return null;
    return d.session;
  }

  /* Demo radio — mirrors the board's /api/radio/now + /api/radio/stats
   * shapes (see social_radio.py) so the single radio section works in
   * demo mode: the sample playlist, looping, with the current track
   * tracked by radioIndex (advanced by the 'ended' handler below). */
  function demoRadioTracks() {
    var d = demoStore();
    return d.tracks.filter(function (t) { return t.status === 'published'; })
      .sort(function (a, b) { return a.id - b.id; });
  }

  function demoRadioCurrent() {
    var q = demoRadioTracks();
    if (!q.length) return null;
    if (radioIndex < 0 || radioIndex >= q.length) radioIndex = 0;
    return q[radioIndex];
  }

  function demoRadioNow() {
    var q = demoRadioTracks();
    var cur = demoRadioCurrent();
    if (!cur) {
      return { on_air: false, station: 'B Heard Radio', track: null,
        started_at: null, ends_at: null, listeners: 0, up_next: [],
        pool_tracks: 0, pool_hours: 0 };
    }
    var idx = q.indexOf(cur);
    var up = q.slice(idx + 1, idx + 4).map(function (t) {
      var u = demoUserById(t.user_id) || {};
      return { title: t.title, artist: u.display || 'Demo artist' };
    });
    var cu = demoUserById(cur.user_id) || {};
    return { on_air: true, station: 'B Heard Radio',
      track: { title: cur.title, artist: cu.display || 'Demo artist' },
      started_at: null, ends_at: null, listeners: null, up_next: up,
      pool_tracks: q.length, pool_hours: 0 };
  }

  function demoRadioStats() {
    return { on_air: true, station: 'B Heard Radio',
      estimated_unique_listeners: 0, total_plays: 0, listeners_now: 0,
      total_connections: 0 };
  }

  function demoHandle(method, path, query, body, headers) {
    var d = demoStore();
    var me = d.session;
    var m;

    if (method === 'GET' && path === 'config') return jsonResponse({ googleClientId: null });
    if (method === 'GET' && path === 'me') return jsonResponse({ user: me ? publicProfile(me) : null });

    if (method === 'GET' && path === 'radio/now') return jsonResponse(demoRadioNow());
    if (method === 'GET' && path === 'radio/stats') return jsonResponse(demoRadioStats());

    if (method === 'POST' && path === 'login') {
      var user = d.users.find(function (u) { return u.email === (body.email || '').toLowerCase(); });
      if (!user) return demoError('No demo account with that email. Register one, or sign in as demo_alice@example.invalid (any password).', 401);
      d.session = user;
      storeSet(SESSION_KEY, user.handle);
      return jsonResponse({ user: publicProfile(user) });
    }
    if (method === 'POST' && path === 'register') {
      var handle = String(body.handle || '').toLowerCase();
      if (!HANDLE_RE.test(handle)) return demoError('Handle must be 3-24 lowercase letters, digits or underscores.');
      if (demoUserByHandle(handle)) return demoError('That handle is taken in the demo.');
      if (!body.email || !body.password || String(body.password).length < 12) return demoError('Demo registration needs an email and a 12+ character password.');
      var display = String(body.display || handle);
      if (display.length < 2 || display.length > 60) return demoError('Artist name must be 2-60 characters.');
      var nu = {
        id: d.nextUserId++, handle: handle, display: display,
        email: String(body.email).toLowerCase(), bio: '', role: 'artist', plan: 'free',
        genre: 'Other', location: '', website: '', links: [],
        theme: { accent: '#e11d48', background: '#09090c', layout: 'grid' },
        avatar_url: null, banner_url: null, pinned_track_id: null, created: nowEpoch()
      };
      d.users.push(nu);
      d.session = nu;
      storeSet(SESSION_KEY, nu.handle);
      return jsonResponse({ user: publicProfile(nu) });
    }
    if (method === 'POST' && path === 'logout') {
      d.session = null;
      storeDel(SESSION_KEY);
      return jsonResponse({ ok: true });
    }

    if (method === 'GET' && path === 'feed') {
      var list = d.tracks.filter(function (t) { return t.status === 'published'; });
      if (query.get('genre')) list = list.filter(function (t) { return t.genre === query.get('genre'); });
      if (query.get('sort') === 'top') list.sort(function (a, b) { return (b.votes || 0) - (a.votes || 0); });
      else list.sort(function (a, b) { return b.created - a.created; });
      return jsonResponse({ tracks: list.slice(0, 100).map(trackJson) });
    }

    if ((m = path.match(/^profile\/([a-z0-9_]{3,24})\/discography$/))) {
      var du = demoUserByHandle(m[1]);
      if (!du) return demoError('Artist not found', 404);
      var ownView = me && me.id === du.id;
      var dts = d.tracks.filter(function (t) {
        return t.user_id === du.id && (ownView || t.status === 'published');
      });
      dts.sort(function (a, b) {
        if (du.pinned_track_id) {
          if (a.id === du.pinned_track_id) return -1;
          if (b.id === du.pinned_track_id) return 1;
        }
        return b.created - a.created;
      });
      return jsonResponse({ artist: publicProfile(du), tracks: dts.map(trackJson) });
    }
    if ((m = path.match(/^profile\/([a-z0-9_]{3,24})$/))) {
      if (method !== 'GET') return demoError('Not found', 404);
      var pu = demoUserByHandle(m[1]);
      if (!pu) return demoError('Artist not found', 404);
      var pts = d.tracks.filter(function (t) { return t.user_id === pu.id && t.status === 'published'; })
        .sort(function (a, b) { return b.created - a.created; });
      return jsonResponse({ artist: publicProfile(pu), tracks: pts.map(trackJson) });
    }
    if (method === 'POST' && path === 'profile') {
      var su = requireSession();
      if (!su) return demoError('Sign in first', 401);
      if (body.display !== undefined) {
        var disp = String(body.display).trim();
        if (disp.length < 2 || disp.length > 60) return demoError('Artist name must be 2-60 characters.');
        su.display = disp;
      }
      if (body.bio !== undefined) {
        if (String(body.bio).length > 1000) return demoError('Bio must be at most 1000 characters.');
        su.bio = String(body.bio);
      }
      if (body.genre !== undefined) {
        if (GENRES.indexOf(body.genre) < 0) return demoError('Unknown genre.');
        su.genre = body.genre;
      }
      if (body.location !== undefined) {
        if (String(body.location).length > 120) return demoError('Location must be at most 120 characters.');
        su.location = String(body.location);
      }
      if (body.website !== undefined) {
        var ws = String(body.website);
        if (ws && (ws.length > 200 || !/^https?:\/\//.test(ws))) return demoError('Website must start with http(s):// and be at most 200 characters.');
        su.website = ws;
      }
      if (body.links !== undefined) {
        if (!Array.isArray(body.links) || body.links.length > 5) return demoError('At most 5 links.');
        for (var li = 0; li < body.links.length; li++) {
          var lk = body.links[li];
          if (!lk || typeof lk.label !== 'string' || lk.label.length < 1 || lk.label.length > 40 ||
              typeof lk.url !== 'string' || lk.url.length < 1 || lk.url.length > 200 || !/^https?:\/\//.test(lk.url)) {
            return demoError('Each link needs a 1-40 character label and an http(s) URL up to 200 characters.');
          }
        }
        su.links = body.links;
      }
      if (body.theme !== undefined) {
        var th = {};
        if (body.theme.accent !== undefined) {
          if (!HEX_COLOR_RE.test(body.theme.accent)) return demoError('Accent must be a #rrggbb colour.');
          th.accent = body.theme.accent;
        }
        if (body.theme.background !== undefined) {
          if (!HEX_COLOR_RE.test(body.theme.background)) return demoError('Background must be a #rrggbb colour.');
          th.background = body.theme.background;
        }
        if (body.theme.layout !== undefined) {
          if (body.theme.layout !== 'grid' && body.theme.layout !== 'list') return demoError('Layout must be grid or list.');
          th.layout = body.theme.layout;
        }
        su.theme = th;
      }
      if (body.pinned_track_id !== undefined) {
        if (body.pinned_track_id === null) { su.pinned_track_id = null; }
        else {
          var pt2 = demoTrackById(Number(body.pinned_track_id));
          if (!pt2 || pt2.user_id !== su.id || pt2.status !== 'published') return demoError('Pinned track must be one of your published tracks.');
          su.pinned_track_id = pt2.id;
        }
      }
      return jsonResponse({ user: publicProfile(su) });
    }
    if (method === 'POST' && (path === 'profile/avatar' || path === 'profile/banner')) {
      if (!requireSession()) return demoError('Sign in first', 401);
      return jsonResponse({ ok: true, note: 'Demo mode does not store images.' });
    }

    if (method === 'POST' && path === 'upload') {
      var uu = requireSession();
      if (!uu) return demoError('Sign in first', 401);
      var title = String((headers['x-track-title'] || '')).trim();
      if (!title || title.length > 100) return demoError('Track title is required (max 100 characters).');
      var genre = headers['x-track-genre'] || 'Other';
      if (GENRES.indexOf(genre) < 0) genre = 'Other';
      var nt = {
        id: d.nextTrackId++, user_id: uu.id, title: title, genre: genre,
        description: String(headers['x-track-description'] || '').slice(0, 500),
        created: nowEpoch(), votes: 0, status: 'published'
      };
      d.tracks.push(nt);
      return jsonResponse({ track: trackJson(nt) });
    }

    if (method === 'POST' && path === 'vote') {
      var vu = requireSession();
      if (!vu) return demoError('Sign in to vote', 401);
      var vt = demoTrackById(Number(body.trackId));
      if (!vt || vt.status !== 'published') return demoError('Track not found', 404);
      var vkey = vu.id + ':' + vt.id;
      var voted;
      if (d.votes.has(vkey)) { d.votes.delete(vkey); vt.votes = Math.max(0, (vt.votes || 0) - 1); voted = false; }
      else { d.votes.add(vkey); vt.votes = (vt.votes || 0) + 1; voted = true; }
      return jsonResponse({ voted: voted, votes: vt.votes });
    }
    if (method === 'POST' && path === 'follow') {
      var fu = requireSession();
      if (!fu) return demoError('Sign in to follow', 401);
      var fa = demoUserById(Number(body.artistId));
      if (!fa) return demoError('Artist not found', 404);
      if (fa.id === fu.id) return demoError('You cannot follow yourself.');
      var fkey = fu.id + ':' + fa.id;
      var following;
      if (d.follows.has(fkey)) { d.follows.delete(fkey); following = false; }
      else { d.follows.add(fkey); following = true; }
      return jsonResponse({ following: following });
    }
    if (method === 'POST' && path === 'report') return jsonResponse({ ok: true });

    /* Artist control (added by the v2 audit 2026-11-10): hide/unhide one
     * of your own tracks. Demo implements it; live mode depends on the
     * coordinator wiring POST /api/track/<id>/visibility on the Dell. */
    if ((m = path.match(/^track\/(\d+)\/visibility$/)) && method === 'POST') {
      var tu = requireSession();
      if (!tu) return demoError('Sign in first', 401);
      var tt = demoTrackById(Number(m[1]));
      if (!tt) return demoError('Track not found', 404);
      if (tt.user_id !== tu.id) return demoError('Only the track owner can change visibility.', 403);
      if (body.status !== 'hidden' && body.status !== 'published') return demoError('Status must be hidden or published.');
      tt.status = body.status;
      return jsonResponse({ ok: true, status: tt.status });
    }

    if (method === 'GET' && path === 'posts') {
      var feed = query.get('feed') || 'all';
      var viewer = d.session ? d.session.id : null;
      var plist = d.posts.filter(function (p) { return p.status === 'published'; });
      if (feed === 'following') {
        if (!d.session) return demoError('Sign in to see posts from people you follow', 401);
        var followed = new Set(Array.from(d.follows)
          .filter(function (k) { return Number(k.split(':')[0]) === d.session.id; })
          .map(function (k) { return Number(k.split(':')[1]); }));
        followed.add(d.session.id);
        plist = plist.filter(function (p) { return followed.has(p.author_id); });
      }
      plist.sort(function (a, b) { return (b.created - a.created) || (b.id - a.id); });
      var before = query.get('before') ? Number(query.get('before')) : null;
      if (before) plist = plist.filter(function (p) { return p.id < before; });
      var limit = Math.min(20, Math.max(1, Number(query.get('limit') || 20)));
      var page = plist.slice(0, limit);
      var nextBefore = plist.length > limit ? page[page.length - 1].id : null;
      return jsonResponse({ posts: page.map(function (p) { return postJson(p, viewer); }), next_before: nextBefore });
    }
    if (method === 'POST' && path === 'posts') {
      var au = requireSession();
      if (!au) return demoError('Sign in to post', 401);
      if (body.kind === 'text') {
        if (typeof body.body !== 'string' || body.body.trim().length < 1 || body.body.length > 2000) return demoError('Text posts need 1-2000 characters.');
        if (body.track_id) return demoError('Text posts cannot carry a track.');
      } else if (body.kind === 'music') {
        var mt = demoTrackById(Number(body.track_id));
        if (!mt || mt.status !== 'published' || mt.user_id !== au.id) return demoError('Music posts need one of your published tracks.');
        if (body.body && body.body.length > 500) return demoError('Music post captions are at most 500 characters.');
      } else {
        return demoError('Post kind must be text or music.');
      }
      var np = {
        id: d.nextPostId++, author_id: au.id, kind: body.kind,
        body: String(body.body || ''), track_id: body.kind === 'music' ? Number(body.track_id) : null,
        created: nowEpoch(), updated_at: nowEpoch(), status: 'published'
      };
      d.posts.push(np);
      return jsonResponse({ post: postJson(np, au.id) });
    }
    if ((m = path.match(/^posts\/(\d+)\/like$/)) && method === 'POST') {
      var lu = requireSession();
      if (!lu) return demoError('Sign in to like', 401);
      var lp = d.posts.find(function (p) { return p.id === Number(m[1]); });
      if (!lp || lp.status !== 'published') return demoError('Post not found', 404);
      var lkey = lu.id + ':' + lp.id;
      var liked;
      if (d.postLikes.has(lkey)) { d.postLikes.delete(lkey); liked = false; }
      else { d.postLikes.add(lkey); liked = true; }
      return jsonResponse({ liked: liked, like_count: postJson(lp, lu.id).like_count });
    }
    if ((m = path.match(/^posts\/(\d+)\/comments$/))) {
      var cp = d.posts.find(function (p) { return p.id === Number(m[1]); });
      if (!cp || cp.status !== 'published') return demoError('Post not found', 404);
      if (method === 'GET') {
        var clist = d.comments.filter(function (c) { return c.post_id === cp.id && c.status === 'published'; })
          .sort(function (a, b) { return a.created - b.created; })
          .map(function (c) {
            var ca = demoUserById(c.author_id) || { id: 0, handle: 'demo_unknown', display: 'Demo artist', avatar_url: null };
            return { id: c.id, post_id: c.post_id, body: c.body, created_at: c.created,
                     author: { id: ca.id, handle: ca.handle, display: ca.display, avatar_url: ca.avatar_url || null } };
          });
        return jsonResponse({ comments: clist });
      }
      if (method === 'POST') {
        var cu = requireSession();
        if (!cu) return demoError('Sign in to comment', 401);
        if (typeof body.body !== 'string' || body.body.trim().length < 1 || body.body.length > 1000) return demoError('Comments need 1-1000 characters.');
        var nc = { id: d.nextCommentId++, post_id: cp.id, author_id: cu.id, body: String(body.body), created: nowEpoch(), status: 'published' };
        d.comments.push(nc);
        return jsonResponse({ comment: { id: nc.id, post_id: nc.post_id, body: nc.body, created_at: nc.created,
          author: { id: cu.id, handle: cu.handle, display: cu.display, avatar_url: null } } });
      }
    }
    if ((m = path.match(/^posts\/(\d+)$/)) && method === 'DELETE') {
      var du2 = requireSession();
      if (!du2) return demoError('Sign in first', 401);
      var dp = d.posts.find(function (p) { return p.id === Number(m[1]); });
      if (!dp) return demoError('Post not found', 404);
      if (dp.author_id !== du2.id && du2.role !== 'admin') return demoError('Only the author can delete this post.', 403);
      dp.status = 'hidden';
      return jsonResponse({ ok: true });
    }
    if ((m = path.match(/^posts\/comments\/(\d+)$/)) && method === 'DELETE') {
      var du3 = requireSession();
      if (!du3) return demoError('Sign in first', 401);
      var dc = d.comments.find(function (c) { return c.id === Number(m[1]); });
      if (!dc) return demoError('Comment not found', 404);
      if (dc.author_id !== du3.id && du3.role !== 'admin') return demoError('Only the author can delete this comment.', 403);
      dc.status = 'hidden';
      return jsonResponse({ ok: true });
    }

    if (method === 'POST' && path === 'checkout') {
      return demoError('Creator checkout is not available in demo mode — connect to the live network.', 400);
    }
    if (method === 'POST' && path === 'google') {
      return demoError('Google sign-in is not available in demo mode.', 400);
    }
    return demoError('Demo mode: unknown endpoint /api/' + path, 404);
  }

  async function demoFetch(input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    init = init || {};
    var method = (init.method || 'GET').toUpperCase();
    if (url.indexOf('/media/') === 0) {
      var mid = url.split('/').pop().split('.')[0];
      return nativeFetch(toneFor(mid));
    }
    var rest = url.slice(5); // strip '/api/'
    var qpos = rest.indexOf('?');
    var path = qpos >= 0 ? rest.slice(0, qpos) : rest;
    var query = new URLSearchParams(qpos >= 0 ? rest.slice(qpos + 1) : '');
    var body = {};
    if (typeof init.body === 'string' && init.body) {
      try { body = JSON.parse(init.body); } catch (e) { body = {}; }
    }
    var headers = {};
    if (init.headers) {
      Object.keys(init.headers).forEach(function (k) { headers[k.toLowerCase()] = init.headers[k]; });
    }
    return demoHandle(method, path, query, body, headers);
  }

  /* ------------------------------------------------------------------ */
  /* Patched fetch: queue API calls behind detection, then route         */
  /* ------------------------------------------------------------------ */
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    if (url.indexOf('/api/') === 0 || url.indexOf('/media/') === 0) {
      return ready.then(function () {
        if (state.mode === 'live') return liveFetch(input, init);
        return demoFetch(input, init);
      });
    }
    return nativeFetch(input, init);
  };

  window.BHEARD = {
    get mode() { return state.mode; },
    get apiBase() { return state.apiBase; },
    ready: ready,
    detect: function () { return ready; }
  };

  /* ------------------------------------------------------------------ */
  /* Radio + connect-form wiring (runs once the DOM is ready)            */
  /* ------------------------------------------------------------------ */
  /* Demo radio position: which sample track the looping demo playlist is
   * on. The single radio section itself is driven by social-radio.js;
   * this shim only maps '/radio/stream' and advances the demo queue. */
  var radioIndex = -1;

  function wireDemoRadioAdvance() {
    var audio = $('#audio');
    if (!audio) return;
    audio.addEventListener('ended', function () {
      if (state.mode !== 'demo') return;
      if (!audio.dataset || audio.dataset.radioStream !== '1') return;
      var q = demoRadioTracks();
      if (!q.length) return;
      radioIndex = (radioIndex + 1) % q.length;
      audio.src = '/radio/stream';
      var np = $('#nowplaying');
      var t = q[radioIndex];
      var u = demoUserById(t.user_id) || {};
      if (np) np.textContent = t.title + (u.display ? ' — ' + u.display : '') + ' · B Heard Radio (demo)';
      audio.play().catch(function () {});
    });
  }

  function wireConnectForm() {
    var form = $('#bheard-connect-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = $('#bheard-api-input');
      var status = $('#bheard-connect-status');
      var value = (input.value || '').trim().replace(/\/+$/, '');
      if (!value) { storeDel(LS_KEY); window.location.reload(); return; }
      if (!/^https?:\/\//.test(value)) {
        if (status) status.textContent = 'Enter a full address starting with https://';
        return;
      }
      storeSet(LS_KEY, value);
      if (status) status.textContent = 'Saved — reloading to connect…';
      window.location.reload();
    });
    var demoBtn = $('#bheard-demo-btn');
    if (demoBtn) demoBtn.addEventListener('click', function () {
      storeDel(LS_KEY);
      window.location.reload();
    });
  }

  function init() {
    wireDemoRadioAdvance();
    wireConnectForm();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

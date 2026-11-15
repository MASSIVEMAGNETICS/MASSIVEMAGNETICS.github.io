#!/usr/bin/env node
/* B Heard Network — demo-store functional check (node, no dependencies).
 *
 * Loads bheardnetwork/demo-data.js + bheard-api.js in a vm sandbox with a
 * minimal DOM stub, forces demo mode (the API probe 404s), then exercises
 * the demo store end to end: sign-in, feed, profiles, discography, posts,
 * likes, comments, votes, follows, upload, hide/unhide, checkout block,
 * media tones, logout. Exits non-zero on the first failure.
 *
 * Run: node tests/bheardnetwork_demo_check.js   (from the site-mm root)
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const BH = path.join(ROOT, 'bheardnetwork');

let failures = 0;
function check(name, cond, extra) {
  if (cond) { console.log('PASS ' + name); }
  else { failures++; console.log('FAIL ' + name + (extra !== undefined ? ' :: ' + JSON.stringify(extra) : '')); }
}
function eq(name, got, want) { check(name, got === want, { got, want }); }

async function main() {
  // ---- minimal browser stub -------------------------------------------
  // Fake <audio> element: lets the harness prove the shim's src patch
  // (radio stream -> demo tone + marker, track src -> tone, marker clear).
  function FakeMedia() { this.dataset = {}; this._src = ''; }
  Object.defineProperty(FakeMedia.prototype, 'src', {
    get() { return this._src; },
    set(v) { this._src = v; },
    configurable: true,
  });
  const storage = new Map();
  const sandbox = {
    console,
    setTimeout, clearTimeout,
    Response, URL, URLSearchParams,
    HTMLMediaElement: FakeMedia,
    location: { search: '', href: 'https://example.invalid/bheardnetwork/', reload() {} },
    document: {
      readyState: 'complete',
      querySelector() { return null; },
      addEventListener() {},
    },
    localStorage: {
      getItem(k) { return storage.has(k) ? storage.get(k) : null; },
      setItem(k, v) { storage.set(k, String(v)); },
      removeItem(k) { storage.delete(k); },
    },
    fetch: async (url) => {
      if (typeof url === 'string' && url.indexOf('demo-media/') === 0) {
        return new Response('RIFFfake', { status: 200, headers: { 'Content-Type': 'audio/wav' } });
      }
      return new Response('not found', { status: 404, headers: { 'Content-Type': 'text/html' } });
    },
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(BH, 'demo-data.js'), 'utf8'), sandbox, { filename: 'demo-data.js' });
  vm.runInContext(fs.readFileSync(path.join(BH, 'bheard-api.js'), 'utf8'), sandbox, { filename: 'bheard-api.js' });

  const fetchApi = sandbox.window.fetch;
  const state = await sandbox.window.BHEARD_READY;
  eq('detection falls back to demo mode (probe 404s)', state.mode, 'demo');

  // Radio src patch: the single radio section's stream URL must resolve
  // to a demo tone in demo mode, and the radioStream marker must track it.
  const m = new sandbox.HTMLMediaElement();
  m.src = '/radio/stream';
  eq('demo radio stream src maps to first demo tone', m.src, 'demo-media/1.wav');
  eq('demo radio stream sets marker', m.dataset.radioStream, '1');
  m.src = '/media/2';
  eq('track src maps to tone 2', m.src, 'demo-media/2.wav');
  eq('track src clears radio marker', m.dataset.radioStream, undefined);

  async function call(method, p, body, headers) {
    const init = { method, headers: { 'Content-Type': 'application/json', ...(headers || {}) } };
    if (body !== undefined) init.body = typeof body === 'string' ? body : JSON.stringify(body);
    const r = await fetchApi('/api/' + p, init);
    let d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    return { status: r.status, ok: r.ok, data: d };
  }
  async function get(p) { return call('GET', p); }

  let r;
  r = await get('config');
  eq('config has no google client in demo', r.data && r.data.googleClientId, null);

  r = await get('me');
  eq('me is null before sign-in', r.data && r.data.user, null);

  r = await call('POST', 'login', { email: 'nobody@example.invalid', password: 'x'.repeat(12) });
  eq('login with unknown email is 401', r.status, 401);

  r = await call('POST', 'login', { email: 'demo_alice@example.invalid', password: 'any-password-here' });
  eq('demo login succeeds', r.status, 200);
  eq('demo login user is demo_alice', r.data && r.data.user && r.data.user.handle, 'demo_alice');

  r = await get('feed');
  eq('feed has 4 demo tracks', r.data && r.data.tracks && r.data.tracks.length, 4);
  eq('feed newest first (track 4 first)', r.data.tracks[0].id, 4);
  check('feed tracks carry demo media urls', r.data.tracks.every((t) => /^demo-media\/[1-4]\.wav$/.test(t.media_url)), r.data.tracks.map((t) => t.media_url));
  check('feed tracks carry status', r.data.tracks.every((t) => t.status === 'published'));

  r = await get('feed?sort=top');
  eq('feed sort=top puts most-voted first', r.data.tracks[0].id, 1);

  r = await get('profile/demo_alice');
  eq('profile artist handle', r.data.artist.handle, 'demo_alice');
  eq('profile followers_count', r.data.artist.followers_count, 2);
  eq('profile track_count', r.data.artist.track_count, 2);
  eq('profile tracks length', r.data.tracks.length, 2);

  r = await get('profile/demo_alice/discography');
  eq('discography pinned track first', r.data.tracks[0].id, 1);

  r = await get('posts?feed=all');
  eq('posts feed has 3 demo posts', r.data.posts.length, 3);
  eq('posts newest first', r.data.posts[0].id, 3);
  check('music post carries track', r.data.posts.find((p) => p.id === 2).track !== null);

  r = await call('POST', 'posts', { kind: 'text', body: 'Demo check post' });
  eq('create text post ok', r.status, 200);
  eq('new post id is 4', r.data.post.id, 4);

  r = await call('POST', 'posts/4/like', {});
  eq('like post toggles on', r.data.liked, true);
  r = await get('posts?feed=all');
  eq('liked post shows like_count 1', r.data.posts.find((p) => p.id === 4).like_count, 1);

  r = await call('POST', 'posts/4/comments', { body: 'Demo check comment' });
  eq('add comment ok', r.status, 200);
  r = await get('posts/4/comments');
  eq('comment thread has 1 comment', r.data.comments.length, 1);

  r = await call('POST', 'vote', { trackId: 2 });
  eq('vote toggles on', r.data.voted, true);
  eq('vote count 2 -> 3', r.data.votes, 3);

  r = await call('POST', 'follow', { artistId: 3 });
  eq('follow toggles on', r.data.following, true);

  r = await call('POST', 'upload', undefined, {
    'X-Track-Title': 'Demo Upload', 'X-Track-Genre': 'Hip-Hop', 'X-Track-Description': 'harness upload',
  });
  eq('demo upload ok', r.status, 200);
  eq('uploaded track id is 5', r.data.track.id, 5);
  r = await get('feed');
  eq('feed has 5 tracks after upload', r.data.tracks.length, 5);

  r = await call('POST', 'track/5/visibility', { status: 'hidden' });
  eq('hide own track ok', r.status, 200);
  r = await get('profile/demo_alice/discography');
  check('owner discography still shows hidden track', r.data.tracks.some((t) => t.id === 5 && t.status === 'hidden'));
  r = await get('feed');
  eq('feed excludes hidden track', r.data.tracks.length, 4);
  r = await call('POST', 'track/5/visibility', { status: 'published' });
  eq('unhide own track ok', r.status, 200);

  r = await call('POST', 'track/3/visibility', { status: 'hidden' });
  eq('cannot hide someone else track (403)', r.status, 403);

  r = await get('radio/now');
  eq('radio now is on air in demo', r.data && r.data.on_air, true);
  eq('radio now track is first demo track', r.data && r.data.track && r.data.track.title, 'Demo Drop One');
  eq('radio now up_next has 3', r.data && r.data.up_next && r.data.up_next.length, 3);
  check('radio now up_next titles', (r.data.up_next || []).map((t) => t.title).join('|') === 'Demo Drop Two|Demo Rock Sketch|Demo Slow Jam');

  r = await get('radio/stats');
  eq('radio stats on air in demo', r.data && r.data.on_air, true);
  eq('radio stats unique listeners 0', r.data && r.data.estimated_unique_listeners, 0);

  r = await call('POST', 'checkout', {});
  eq('checkout blocked in demo (400)', r.status, 400);
  check('checkout error says demo mode', /demo mode/i.test(r.data.error || ''));

  r = await fetchApi('/media/1');
  eq('demo media fetch returns tone', r.status, 200);

  r = await call('POST', 'logout', {});
  eq('logout ok', r.status, 200);
  r = await get('me');
  eq('me is null after logout', r.data.user, null);
  r = await call('POST', 'posts', { kind: 'text', body: 'should fail' });
  eq('posting signed out is 401', r.status, 401);

  if (failures) { console.log('\n' + failures + ' FAILURE(S)'); process.exit(1); }
  console.log('\nAll demo-store checks passed.');
}

main().catch((e) => { console.error('HARNESS ERROR', e); process.exit(1); });

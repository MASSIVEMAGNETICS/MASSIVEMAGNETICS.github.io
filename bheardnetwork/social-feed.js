'use strict';
/* B Heard Network: social feed UI (Slice B, v2 contract §3.6).
   NEW file only. Uses the shared app.js globals ($, esc, api, post, notice,
   me, openAuth) — never redefines them. No inline handlers, no external
   URLs, all user text through esc().
   Music-post play buttons use data-social-play="<trackId>" only.
   Playback of those buttons is owned by social-player.js (Slice C), which
   drives the single shared #player / #audio element; this file only
   renders the buttons. There is no post-report UI in v2 (known gap, §3.2). */
let socialTab = 'all';
let socialBefore = null;
let socialLoading = false;

function socialFeedEl() { return $('#social-posts'); }

function socialPostCard(p) {
  const canDelete = me && (me.id === p.author.id || me.role === 'admin');
  const trackHtml = p.track ? '<div class="row"><button class="primary" type="button" data-social-play="' + p.track.id + '">▶ Listen</button><span><strong>' + esc(p.track.title) + '</strong> — ' + esc(p.track.display) + '</span></div>' : '';
  const avatar = p.author.avatar_url ? '<img src="' + esc(p.author.avatar_url) + '" alt="" width="32" height="32">' : '';
  return '<article class="card" data-social-post="' + p.id + '">'
    + '<div class="row">' + avatar + '<span><strong>' + esc(p.author.display) + '</strong> <a href="#artist/' + encodeURIComponent(p.author.handle) + '">@' + esc(p.author.handle) + '</a></span></div>'
    + '<p>' + esc(p.body) + '</p>'
    + trackHtml
    + '<p><small>' + esc(new Date(p.created_at * 1000).toLocaleString()) + '</small></p>'
    + '<div class="row">'
    + '<button class="outline" type="button" data-social-like="' + p.id + '">♥ ' + Number(p.like_count || 0) + (p.liked_by_me ? ' · Liked' : '') + '</button>'
    + '<button class="outline" type="button" data-social-comments="' + p.id + '">💬 ' + Number(p.comment_count || 0) + ' comments</button>'
    + (canDelete ? '<button class="outline" type="button" data-social-delete="' + p.id + '">Delete</button>' : '')
    + '</div>'
    + '<div data-social-thread="' + p.id + '" hidden></div>'
    + '</article>';
}

function socialRender(posts, append) {
  const box = socialFeedEl();
  if (!box) return;
  if (!append) box.replaceChildren();
  if (!posts.length && !append) {
    box.innerHTML = '<div class="empty">No posts yet. Be the first to share.</div>';
    return;
  }
  const wrap = document.createElement('div');
  wrap.innerHTML = posts.map(socialPostCard).join('');
  while (wrap.firstChild) box.appendChild(wrap.firstChild);
}

async function loadSocialFeed(feed, append) {
  const box = socialFeedEl();
  if (!box || socialLoading) return;
  if (feed === 'following' && !me) { openAuth(); return; }
  socialLoading = true;
  try {
    const q = new URLSearchParams({ feed: feed, limit: '20' });
    if (append && socialBefore) q.set('before', String(socialBefore));
    const r = await api('posts?' + q);
    socialRender(r.posts || [], append);
    socialBefore = r.next_before || null;
    const more = $('#social-more');
    if (more) more.hidden = !socialBefore;
  } catch (e) { notice(e.message); }
  finally { socialLoading = false; }
}

function socialSetTab(feed) {
  socialTab = feed;
  socialBefore = null;
  const allBtn = $('#social-tab-all');
  const folBtn = $('#social-tab-following');
  if (allBtn) allBtn.classList.toggle('primary', feed === 'all');
  if (folBtn) folBtn.classList.toggle('primary', feed === 'following');
  loadSocialFeed(feed, false);
}

async function socialLoadComments(postId, thread) {
  try {
    const r = await api('posts/' + postId + '/comments');
    const list = (r.comments || []).map(function (cm) {
      const author = cm.author || {};
      return '<p><strong>' + esc(author.display || 'Unknown') + '</strong> ' + esc(cm.body) + ' <small>' + esc(new Date(cm.created_at * 1000).toLocaleString()) + '</small></p>';
    }).join('') || '<p><small>No comments yet.</small></p>';
    thread.innerHTML = list
      + '<form data-social-comment-form="' + postId + '"><label>Add a comment<input name="body" maxlength="1000" required></label><button class="primary" type="submit">Comment</button></form>';
    thread.hidden = false;
  } catch (e) { notice(e.message); }
}

async function socialRefreshComposerTracks() {
  const picker = $('#social-track-picker');
  if (!picker || !me) return;
  try {
    const r = await api('profile/' + encodeURIComponent(me.handle));
    const myTracks = r.tracks || [];
    picker.replaceChildren();
    if (!myTracks.length) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No published tracks yet — upload one first';
      picker.append(opt);
      return;
    }
    myTracks.forEach(function (t) {
      const opt = document.createElement('option');
      opt.value = String(t.id);
      opt.textContent = t.title;
      picker.append(opt);
    });
  } catch (e) { notice(e.message); }
}

function socialInit() {
  const section = $('#social-feed');
  if (!section) return;
  const allBtn = $('#social-tab-all');
  const folBtn = $('#social-tab-following');
  if (allBtn) allBtn.addEventListener('click', function () { socialSetTab('all'); });
  if (folBtn) folBtn.addEventListener('click', function () { socialSetTab('following'); });
  const more = $('#social-more');
  if (more) more.addEventListener('click', function () { loadSocialFeed(socialTab, true); });
  const nav = $('#socialnav');
  if (nav) nav.addEventListener('click', function () {
    section.scrollIntoView();
    loadSocialFeed(socialTab, false);
  });
  const kindSel = $('#social-kind');
  const pickerRow = $('#social-track-row');
  if (kindSel && pickerRow) kindSel.addEventListener('change', function () {
    const isMusic = kindSel.value === 'music';
    pickerRow.hidden = !isMusic;
    if (isMusic) socialRefreshComposerTracks();
  });
  const form = $('#social-composer');
  if (form) form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (!me) { openAuth(); return; }
    const body = form.elements.body.value.trim();
    const kind = form.elements.kind.value;
    const data = { kind: kind, body: body };
    if (kind === 'music') {
      const trackId = form.elements.track_id.value;
      if (!trackId) { notice('Pick one of your published tracks for a music post'); return; }
      data.track_id = Number(trackId);
    }
    try {
      await post('posts', data);
      form.reset();
      if (pickerRow) pickerRow.hidden = true;
      notice(kind === 'music' ? 'Music post published' : 'Post published');
      socialBefore = null;
      loadSocialFeed(socialTab, false);
    } catch (err) { notice(err.message); }
  });
  section.addEventListener('click', async function (e) {
    const likeBtn = e.target.closest('[data-social-like]');
    if (likeBtn) {
      if (!me) { openAuth(); return; }
      try {
        await post('posts/' + likeBtn.dataset.socialLike + '/like', {});
        loadSocialFeed(socialTab, false);
      } catch (err) { notice(err.message); }
      return;
    }
    const commentsBtn = e.target.closest('[data-social-comments]');
    if (commentsBtn) {
      const postId = commentsBtn.dataset.socialComments;
      const thread = section.querySelector('[data-social-thread="' + postId + '"]');
      if (!thread) return;
      if (thread.hidden) socialLoadComments(postId, thread);
      else thread.hidden = true;
      return;
    }
    const delBtn = e.target.closest('[data-social-delete]');
    if (delBtn) {
      if (!window.confirm('Delete this post?')) return;
      try {
        await api('posts/' + delBtn.dataset.socialDelete, { method: 'DELETE' });
        loadSocialFeed(socialTab, false);
      } catch (err) { notice(err.message); }
      return;
    }
  });
  section.addEventListener('submit', async function (e) {
    const commentForm = e.target.closest('[data-social-comment-form]');
    if (!commentForm) return;
    e.preventDefault();
    if (!me) { openAuth(); return; }
    const postId = commentForm.dataset.socialCommentForm;
    const body = commentForm.elements.body.value.trim();
    if (!body) return;
    try {
      await post('posts/' + postId + '/comments', { body: body });
      const thread = section.querySelector('[data-social-thread="' + postId + '"]');
      if (thread) socialLoadComments(postId, thread);
      loadSocialFeed(socialTab, false);
    } catch (err) { notice(err.message); }
  });
  loadSocialFeed('all', false);
}

socialInit();

'use strict';
/* B Heard Network — Slice A: profiles & customization (social-profiles.js).
 * NEW file only. Uses the shared globals from app.js ($, esc, api, post,
 * notice, me, view, trackCard, show) — never redefines them. No inline
 * handlers, no external URLs, all user text through esc(). Theme CSS
 * variables are applied to the profile card only, never to the whole site.
 * The coordinator merges the matching HTML snippet (dialog + edit button)
 * into index.html; this file wires it up and enhances the artist view.
 */
(function () {
  var MAX_IMAGE_BYTES = 5 * 1024 * 1024;
  var GENRES = ['Hip-Hop', 'Rock', 'Pop', 'R&B', 'Electronic', 'Country', 'Other'];
  var URL_RE = /^(https?:\/\/)/;
  var enhancing = false;

  function themeStyle(theme) {
    theme = theme || {};
    var parts = [];
    if (theme.accent) parts.push('--sp-accent:' + esc(theme.accent));
    if (theme.background) parts.push('--sp-background:' + esc(theme.background));
    return parts.length ? ' style="' + parts.join(';') + '" data-sp-layout="' + esc(theme.layout || 'grid') + '"' : '';
  }

  function renderSocialProfileCard(artist, tracks) {
    var pinned = artist.pinned_track || null;
    var links = (artist.links || []).map(function (link) {
      return '<li><a href="' + esc(link.url) + '" target="_blank" rel="noopener">' + esc(link.label) + '</a></li>';
    }).join('');
    var pinnedHtml = '';
    if (pinned) {
      pinnedHtml = '<div class="card social-pinned"><span class="eyebrow">PINNED TRACK</span><h3>' +
        esc(pinned.title) + '</h3><p>' + esc(pinned.genre) + ' · ♥ ' + Number(pinned.votes || 0) + '</p></div>';
    }
    var trackHtml = (tracks || []).map(function (t) {
      return trackCard({ id: t.id, title: t.title, genre: t.genre, description: t.description, handle: artist.handle, display: artist.display, votes: 0 });
    }).join('');
    var editBtn = (me && me.handle === artist.handle)
      ? '<button id="social-profile-edit" class="outline">Edit profile</button>' : '';
    return '<div id="social-profile-card" class="card social-profile" data-social-profile="1"' + themeStyle(artist.theme) + '>' +
      (artist.banner_url ? '<img class="social-banner" src="' + esc(artist.banner_url) + '" alt="">' : '') +
      '<div class="row">' +
      (artist.avatar_url ? '<img class="social-avatar" src="' + esc(artist.avatar_url) + '" alt="">' : '') +
      '<div><h3>' + esc(artist.display) +
      (artist.plan === 'creator' ? ' <span class="eyebrow" style="color:#e11d48">★ CREATOR</span>' : '') + '</h3>' +
      '<p>@' + esc(artist.handle) + ' · ' + esc(artist.genre || 'Other') + '</p></div></div>' +
      '<p>' + esc(artist.bio || 'Independent creator') + '</p>' +
      (artist.location ? '<p>' + esc(artist.location) + '</p>' : '') +
      (artist.website ? '<p><a href="' + esc(artist.website) + '" target="_blank" rel="noopener">' + esc(artist.website) + '</a></p>' : '') +
      (links ? '<ul class="social-links">' + links + '</ul>' : '') +
      '<p><small>' + Number(artist.followers_count || 0) + ' followers · ' +
      Number(artist.following_count || 0) + ' following · ' +
      Number(artist.track_count || 0) + ' tracks</small></p>' +
      '<div class="row"><button id="social-follow-btn" class="outline">Follow artist</button>' + editBtn + '</div>' +
      '</div>' + pinnedHtml + trackHtml;
  }

  function applyThemePreview(theme) {
    var card = $('#social-profile-preview');
    if (!card) return;
    card.style.setProperty('--sp-accent', theme.accent || '');
    card.style.setProperty('--sp-background', theme.background || '');
    card.setAttribute('data-sp-layout', theme.layout || 'grid');
  }

  function readThemeFromForm() {
    return {
      accent: $('#sp-accent').value || '',
      background: $('#sp-background').value || '',
      layout: $('#sp-layout').value || 'grid'
    };
  }

  function parseLinksTextarea() {
    var lines = $('#sp-links').value.split('\n');
    var links = [];
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim();
      if (!line) continue;
      var bar = line.indexOf('|');
      if (bar < 0) throw new Error('Each link line needs "Label | URL"');
      var label = line.slice(0, bar).trim();
      var url = line.slice(bar + 1).trim();
      if (label.length < 1 || label.length > 40) throw new Error('Link labels must be 1-40 characters');
      if (!URL_RE.test(url) || url.length > 200) throw new Error('Link URLs must start with http(s) and be at most 200 characters');
      links.push({ label: label, url: url });
    }
    if (links.length > 5) throw new Error('At most 5 links');
    return links;
  }

  function fillPinnedSelect(tracks) {
    var sel = $('#sp-pinned');
    if (!sel) return;
    sel.replaceChildren();
    var none = document.createElement('option');
    none.value = '';
    none.textContent = 'No pinned track';
    sel.append(none);
    (tracks || []).forEach(function (t) {
      var opt = document.createElement('option');
      opt.value = String(t.id);
      opt.textContent = t.title;
      sel.append(opt);
    });
  }

  async function openSocialProfileEditor() {
    if (!me) { notice('Sign in to edit your profile'); return; }
    try {
      var profile = await api('me');
      var artist = profile.user || {};
      var own = await api('profile/' + encodeURIComponent(me.handle));
      $('#sp-display').value = artist.display || '';
      $('#sp-bio').value = artist.bio || '';
      $('#sp-genre').value = GENRES.indexOf(artist.genre) >= 0 ? artist.genre : 'Other';
      $('#sp-location').value = artist.location || '';
      $('#sp-website').value = artist.website || '';
      $('#sp-links').value = (artist.links || []).map(function (l) { return l.label + ' | ' + l.url; }).join('\n');
      var theme = artist.theme || {};
      $('#sp-accent').value = theme.accent || '#e11d48';
      $('#sp-background').value = theme.background || '#09090c';
      $('#sp-layout').value = theme.layout || 'grid';
      fillPinnedSelect(own.tracks || []);
      if (artist.pinned_track_id) $('#sp-pinned').value = String(artist.pinned_track_id);
      applyThemePreview(readThemeFromForm());
      $('#sp-status').textContent = '';
      $('#social-profile-dialog').showModal();
    } catch (err) { notice(err.message); }
  }

  function checkImageFile(input, previewImg) {
    var file = input.files && input.files[0];
    if (!file) return null;
    if (file.size > MAX_IMAGE_BYTES) {
      notice('Image exceeds 5 MB');
      input.value = '';
      return null;
    }
    if (previewImg) {
      var reader = new FileReader();
      reader.onload = function () { previewImg.src = reader.result; };
      reader.readAsDataURL(file);
    }
    return file;
  }

  async function uploadProfileImage(kind) {
    var input = kind === 'avatar' ? $('#sp-avatar-input') : $('#sp-banner-input');
    var file = input && input.files && input.files[0];
    if (!file) { notice('Choose an image first'); return; }
    if (file.size > MAX_IMAGE_BYTES) { notice('Image exceeds 5 MB'); return; }
    var status = kind === 'avatar' ? $('#sp-avatar-status') : $('#sp-banner-status');
    try {
      status.textContent = 'Uploading…';
      var r = await fetch('/api/profile/' + kind, {
        method: 'POST', headers: { 'X-File-Name': file.name }, body: file, credentials: 'same-origin'
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || 'Upload failed');
      status.textContent = 'Saved';
      notice(kind === 'avatar' ? 'Avatar updated' : 'Banner updated');
    } catch (err) { status.textContent = err.message; notice(err.message); }
  }

  async function enhanceArtistView(handle) {
    if (enhancing) return;
    var grid = $('#grid');
    if (!grid || grid.querySelector('[data-social-profile]')) return;
    enhancing = true;
    try {
      var r = await api('profile/' + encodeURIComponent(handle));
      var artist = r.artist || {};
      /* Only enhance when the extended profile shape is present. */
      if (!('followers_count' in artist)) return;
      grid.innerHTML = renderSocialProfileCard(artist, r.tracks || []);
      var followBtn = $('#social-follow-btn');
      if (followBtn) {
        followBtn.addEventListener('click', async function () {
          if (!me) { notice('Sign in to follow'); return; }
          try {
            var x = await post('follow', { artistId: artist.id });
            notice(x.following ? 'Following artist' : 'Unfollowed artist');
          } catch (err) { notice(err.message); }
        });
      }
      var editBtn = $('#social-profile-edit');
      if (editBtn) editBtn.addEventListener('click', openSocialProfileEditor);
    } catch (err) {
      /* Leave app.js rendering in place if the enhanced fetch fails. */
    } finally { enhancing = false; }
  }

  function initSocialProfiles() {
    var form = $('#social-profile-form');
    if (!form) return;
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      try {
        var links = parseLinksTextarea();
        var theme = readThemeFromForm();
        var pinned = $('#sp-pinned').value;
        var payload = {
          display: $('#sp-display').value.trim(),
          bio: $('#sp-bio').value.trim(),
          genre: $('#sp-genre').value,
          location: $('#sp-location').value.trim(),
          website: $('#sp-website').value.trim(),
          links: links,
          theme: theme,
          pinned_track_id: pinned ? Number(pinned) : null
        };
        await post('profile', payload);
        $('#sp-status').textContent = 'Profile saved';
        notice('Profile saved');
        $('#social-profile-dialog').close();
        if (me) show('artist/' + me.handle);
      } catch (err) {
        $('#sp-status').textContent = err.message;
        notice(err.message);
      }
    });
    ['sp-accent', 'sp-background', 'sp-layout'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('input', function () { applyThemePreview(readThemeFromForm()); });
    });
    var avatarInput = $('#sp-avatar-input');
    if (avatarInput) avatarInput.addEventListener('change', function () {
      checkImageFile(avatarInput, $('#sp-avatar-preview'));
    });
    var bannerInput = $('#sp-banner-input');
    if (bannerInput) bannerInput.addEventListener('change', function () {
      checkImageFile(bannerInput, $('#sp-banner-preview'));
    });
    var avatarBtn = $('#sp-avatar-upload');
    if (avatarBtn) avatarBtn.addEventListener('click', function () { uploadProfileImage('avatar'); });
    var bannerBtn = $('#sp-banner-upload');
    if (bannerBtn) bannerBtn.addEventListener('click', function () { uploadProfileImage('banner'); });
    var editBtn = $('#social-edit-profile-btn');
    if (editBtn) editBtn.addEventListener('click', openSocialProfileEditor);

    var grid = $('#grid');
    if (grid && typeof MutationObserver !== 'undefined') {
      var observer = new MutationObserver(function () {
        if (typeof view === 'string' && view.indexOf('artist/') === 0) {
          enhanceArtistView(view.slice(7));
        }
      });
      observer.observe(grid, { childList: true });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSocialProfiles);
  } else {
    initSocialProfiles();
  }

  window.SocialProfiles = {
    renderSocialProfileCard: renderSocialProfileCard,
    openSocialProfileEditor: openSocialProfileEditor,
    enhanceArtistView: enhanceArtistView
  };
})();

(() => {
  'use strict';
  const state = { feed: null };
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const shortDate = (value) => value ? new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}) : 'unknown';

  function render() {
    if (!state.feed) return;
    const q = $('search').value.trim().toLowerCase();
    const source = $('sourceFilter').value;
    const min = Number($('minScore').value || 0);
    const items = (state.feed.items || []).filter(item => {
      const haystack = `${item.title} ${item.summary} ${item.author}`.toLowerCase();
      return item.score >= min && (source === 'all' || item.source === source) && (!q || haystack.includes(q));
    });
    $('feed').innerHTML = items.length ? items.map(card).join('') : '<div class="empty">No signals match the current filter.</div>';
  }

  function card(item) {
    const b = item.score_breakdown || {};
    return `<article class="card">
      <div class="score"><strong>${Number(item.score).toFixed(0)}</strong><span>SCORE</span></div>
      <div>
        <div class="meta"><span class="pill ${esc(item.source)}">${esc(item.source)}</span><span>${esc(item.author)}</span><span>${esc(shortDate(item.updated_at || item.published_at))}</span></div>
        <h2><a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a></h2>
        <p class="summary">${esc((item.summary || '').slice(0, 420))}</p>
        <div class="breakdown"><span>frontier ${(Number(b.frontier)||0).toFixed(2)}</span><span>recency ${(Number(b.recency)||0).toFixed(2)}</span><span>traction ${(Number(b.traction)||0).toFixed(2)}</span><span>indie ${(Number(b.indie)||0).toFixed(2)}</span><span>repro ${(Number(b.reproducibility)||0).toFixed(2)}</span><span>evidence ${esc((item.evidence_sha256||'').slice(0,12))}</span></div>
      </div>
    </article>`;
  }

  async function boot() {
    try {
      const response = await fetch('./data/feed.json', {cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      state.feed = await response.json();
      $('itemCount').textContent = state.feed.item_count ?? 0;
      $('sourceCount').textContent = state.feed.source_count ?? 0;
      $('lastScan').textContent = shortDate(state.feed.generated_at);
      $('errorCount').textContent = (state.feed.errors || []).length;
      $('feedHash').textContent = `SHA256: ${state.feed.feed_sha256 || 'unknown'}`;
      const healthy = Number(state.feed.item_count || 0) > 0;
      $('healthDot').classList.add(healthy ? 'ok' : 'bad');
      $('healthText').textContent = healthy ? 'RADAR ONLINE' : 'BOOTSTRAP / NO SIGNALS';
      render();
    } catch (error) {
      $('healthDot').classList.add('bad');
      $('healthText').textContent = 'FEED ERROR';
      $('feed').innerHTML = `<div class="empty">Radar feed unavailable: ${esc(error.message)}</div>`;
    }
  }

  ['search','sourceFilter','minScore'].forEach(id => $(id).addEventListener(id === 'search' ? 'input' : 'change', render));
  $('copyHash').addEventListener('click', async () => {
    const hash = state.feed?.feed_sha256 || '';
    if (!hash) return;
    await navigator.clipboard.writeText(hash);
    $('copyHash').textContent = 'HASH COPIED';
    setTimeout(() => $('copyHash').textContent = 'COPY FEED HASH', 1200);
  });
  boot();
})();

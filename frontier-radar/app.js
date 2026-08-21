(() => {
  'use strict';

  const state = {
    feed: null,
    status: null,
    integrityOk: false,
    fileSha256: '',
  };

  const $ = (id) => document.getElementById(id);
  const SOURCE_HOSTS = {
    github: new Set(['github.com']),
    huggingface: new Set(['huggingface.co']),
    arxiv: new Set(['arxiv.org', 'www.arxiv.org', 'export.arxiv.org']),
  };

  function text(value) {
    return document.createTextNode(String(value ?? ''));
  }

  function el(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.appendChild(text(content));
    return node;
  }

  function shortDate(value) {
    if (!value) return 'unknown';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'unknown';
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  function safeSourceUrl(source, raw) {
    try {
      const url = new URL(String(raw));
      if (url.protocol !== 'https:') return null;
      const allowed = SOURCE_HOSTS[source];
      if (!allowed || !allowed.has(url.hostname.toLowerCase())) return null;
      if (url.username || url.password) return null;
      return url.href;
    } catch {
      return null;
    }
  }

  async function sha256Hex(bytes) {
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
  }

  function parseDigest(textValue) {
    const match = String(textValue || '').trim().match(/^([0-9a-f]{64})(?:\s|$)/i);
    return match ? match[1].toLowerCase() : '';
  }

  function setHealth(kind, message) {
    const dot = $('healthDot');
    dot.className = `dot ${kind}`;
    $('healthText').textContent = message;
  }

  function setIntegrity(ok, actual, expected) {
    state.integrityOk = ok;
    state.fileSha256 = actual;
    $('integrityState').textContent = ok ? 'VERIFIED' : 'FAILED';
    $('integrityState').className = ok ? 'verified' : 'failed';
    $('fileHash').textContent = `SHA256 ${actual || 'unknown'}`;
    $('fileHash').title = expected && actual !== expected
      ? `Expected ${expected}`
      : 'Exact SHA-256 of feed.json';
  }

  function validateShape(feed) {
    if (!feed || feed.schema_version !== 'frontier-radar-feed/1.2') {
      throw new Error('Unsupported or missing V1.2 feed schema');
    }
    if (!Array.isArray(feed.items)) throw new Error('Feed items are invalid');
    if (Number(feed.item_count) !== feed.items.length) throw new Error('Feed item count mismatch');
    return feed;
  }

  function renderSourceHealth() {
    const container = $('sourceHealth');
    container.replaceChildren();
    const health = state.feed?.source_health || {};
    for (const source of ['github', 'huggingface', 'arxiv']) {
      const data = health[source] || {};
      const card = el('div', `source-chip ${data.healthy ? 'healthy' : 'degraded'}`);
      card.appendChild(el('strong', '', source === 'huggingface' ? 'HUGGING FACE' : source.toUpperCase()));
      card.appendChild(el(
        'span',
        '',
        `${Number(data.successes || 0)}/${Number(data.requests || 0)} requests · ${Number(data.items || 0)} raw`
      ));
      if (data.last_error) {
        card.title = String(data.last_error).slice(0, 300);
      }
      container.appendChild(card);
    }
  }

  function trendPill(trend) {
    const value = ['breakout', 'rising', 'new', 'stable'].includes(trend) ? trend : 'stable';
    return el('span', `trend ${value}`, value.toUpperCase());
  }

  function metricLine(item) {
    const b = item.score_breakdown || {};
    const wrap = el('div', 'breakdown');
    const values = [
      ['frontier', b.frontier],
      ['recency', b.recency],
      ['traction', b.traction],
      ['indie', b.indie],
      ['repro', b.reproducibility],
      ['novelty', b.novelty],
      ['velocity', b.velocity],
    ];
    for (const [name, value] of values) {
      wrap.appendChild(el('span', '', `${name} ${(Number(value) || 0).toFixed(2)}`));
    }
    wrap.appendChild(el('span', '', `evidence ${String(item.evidence_sha256 || '').slice(0, 12)}`));
    return wrap;
  }

  function queryLine(item) {
    const queries = Array.isArray(item.matched_queries) ? item.matched_queries : [];
    if (!queries.length) return null;
    return el('p', 'queries', `Matched: ${queries.slice(0, 4).join(' · ')}${queries.length > 4 ? ` +${queries.length - 4}` : ''}`);
  }

  function card(item) {
    const article = el('article', 'card');
    article.dataset.trend = String(item.trend || 'stable');

    const score = el('div', 'score');
    score.appendChild(el('strong', '', Number(item.score || 0).toFixed(0)));
    score.appendChild(el('span', '', 'SCORE'));
    if (Number(item.velocity_score || 0) > 0) {
      score.appendChild(el('small', '', `v ${(Number(item.velocity_score) * 100).toFixed(0)}`));
    }

    const body = el('div', 'card-body');
    const meta = el('div', 'meta');
    meta.appendChild(el('span', `pill ${item.source || ''}`, String(item.source || 'unknown')));
    meta.appendChild(trendPill(String(item.trend || 'stable')));
    meta.appendChild(el('span', '', String(item.author || 'unknown')));
    meta.appendChild(el('span', '', shortDate(item.updated_at || item.published_at)));

    const heading = el('h2');
    const safeUrl = safeSourceUrl(String(item.source || ''), item.url);
    if (safeUrl) {
      const anchor = el('a', '', String(item.title || 'Untitled'));
      anchor.href = safeUrl;
      anchor.target = '_blank';
      anchor.rel = 'noopener noreferrer';
      heading.appendChild(anchor);
    } else {
      heading.appendChild(text(String(item.title || 'Untitled')));
    }

    body.appendChild(meta);
    body.appendChild(heading);
    body.appendChild(el('p', 'summary', String(item.summary || '').slice(0, 520)));

    const queries = queryLine(item);
    if (queries) body.appendChild(queries);

    const deltas = item.metric_deltas || {};
    const positive = Object.entries(deltas).filter(([, value]) => Number(value) > 0);
    if (positive.length) {
      body.appendChild(el(
        'p',
        'delta',
        `Observed growth: ${positive.slice(0, 4).map(([key, value]) => `+${Number(value).toLocaleString()} ${key}`).join(' · ')}`
      ));
    }

    body.appendChild(metricLine(item));
    article.appendChild(score);
    article.appendChild(body);
    return article;
  }

  function filteredItems() {
    const q = $('search').value.trim().toLowerCase();
    const source = $('sourceFilter').value;
    const trend = $('trendFilter').value;
    const min = Number($('minScore').value || 0);
    const sortMode = $('sortMode').value;

    const items = (state.feed?.items || []).filter((item) => {
      const haystack = `${item.title || ''} ${item.summary || ''} ${item.author || ''} ${(item.matched_queries || []).join(' ')}`.toLowerCase();
      return Number(item.score || 0) >= min
        && (source === 'all' || item.source === source)
        && (trend === 'all' || item.trend === trend)
        && (!q || haystack.includes(q));
    });

    items.sort((a, b) => {
      if (sortMode === 'velocity') {
        return Number(b.velocity_score || 0) - Number(a.velocity_score || 0)
          || Number(b.score || 0) - Number(a.score || 0);
      }
      if (sortMode === 'newest') {
        return new Date(b.updated_at || b.published_at || 0).getTime()
          - new Date(a.updated_at || a.published_at || 0).getTime();
      }
      const rank = {breakout: 3, rising: 2, new: 1, stable: 0};
      return (rank[b.trend] || 0) - (rank[a.trend] || 0)
        || Number(b.score || 0) - Number(a.score || 0)
        || Number(b.velocity_score || 0) - Number(a.velocity_score || 0);
    });
    return items;
  }

  function render() {
    if (!state.feed || !state.integrityOk) return;
    const container = $('feed');
    container.replaceChildren();
    const items = filteredItems();
    if (!items.length) {
      container.appendChild(el('div', 'empty', 'No signals match the current filters.'));
    } else {
      for (const item of items) container.appendChild(card(item));
    }
    container.setAttribute('aria-busy', 'false');
  }

  function renderMetrics() {
    const feed = state.feed;
    $('itemCount').textContent = Number(feed.item_count || 0).toLocaleString();
    $('breakoutCount').textContent = Number(feed.breakout_count || 0).toLocaleString();
    $('healthySources').textContent = `${Number(feed.healthy_source_count || 0)}/${Number(feed.source_count || 0)}`;
    $('lastScan').textContent = shortDate(feed.generated_at);
    $('scanDuration').textContent = `${(Number(feed.scan_duration_ms || 0) / 1000).toFixed(1)}s`;
    renderSourceHealth();
  }

  async function boot() {
    try {
      const [feedResponse, digestResponse, statusResponse] = await Promise.all([
        fetch('./data/feed.json', {cache: 'no-store'}),
        fetch('./data/feed.sha256', {cache: 'no-store'}),
        fetch('./data/status.json', {cache: 'no-store'}),
      ]);

      if (!feedResponse.ok) throw new Error(`feed HTTP ${feedResponse.status}`);
      if (!digestResponse.ok) throw new Error(`digest HTTP ${digestResponse.status}`);
      if (!statusResponse.ok) throw new Error(`status HTTP ${statusResponse.status}`);

      const [feedBytes, digestText, status] = await Promise.all([
        feedResponse.arrayBuffer(),
        digestResponse.text(),
        statusResponse.json(),
      ]);

      const actual = await sha256Hex(feedBytes);
      const expected = parseDigest(digestText);
      setIntegrity(Boolean(expected) && actual === expected, actual, expected);
      if (!state.integrityOk) {
        setHealth('bad', 'INTEGRITY FAILURE');
        $('feed').replaceChildren(el('div', 'empty danger', 'Snapshot digest mismatch. Feed rendering is blocked.'));
        $('feed').setAttribute('aria-busy', 'false');
        return;
      }

      const decoded = new TextDecoder('utf-8', {fatal: true}).decode(feedBytes);
      state.feed = validateShape(JSON.parse(decoded));
      state.status = status;

      if (status.feed_sha256 && status.feed_sha256 !== state.feed.feed_sha256) {
        throw new Error('Status/feed snapshot mismatch');
      }
      if (status.file_sha256 && status.file_sha256 !== actual) {
        throw new Error('Status/file digest mismatch');
      }

      renderMetrics();
      const healthy = status.healthy === true
        && Number(state.feed.healthy_source_count || 0) >= 2
        && Number(state.feed.item_count || 0) > 0;
      setHealth(healthy ? 'ok' : 'warn', healthy ? 'RADAR ONLINE · VERIFIED' : 'RADAR DEGRADED · VERIFIED');
      render();
    } catch (error) {
      setHealth('bad', 'RADAR ERROR');
      const container = $('feed');
      container.replaceChildren(el('div', 'empty danger', `Radar unavailable: ${error.message}`));
      container.setAttribute('aria-busy', 'false');
    }
  }

  for (const id of ['search', 'sourceFilter', 'trendFilter', 'minScore', 'sortMode']) {
    $(id).addEventListener(id === 'search' ? 'input' : 'change', render);
  }

  $('copyHash').addEventListener('click', async () => {
    const hash = state.fileSha256 || '';
    if (!hash) return;
    try {
      await navigator.clipboard.writeText(hash);
      $('copyHash').textContent = 'HASH COPIED';
      setTimeout(() => {
        $('copyHash').textContent = 'COPY SNAPSHOT HASH';
      }, 1200);
    } catch {
      $('copyHash').textContent = 'COPY BLOCKED';
    }
  });

  boot();
})();

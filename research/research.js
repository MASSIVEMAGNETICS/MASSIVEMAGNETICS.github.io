(() => {
  'use strict';
  const REGISTRY_URL = '/registry/public/research.json';
  const COMMIT_BASE = 'https://github.com/MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io/commit/';
  const $ = (id) => document.getElementById(id);
  const esc = (v = '') => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav-links');
  if (menu && nav) menu.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
    menu.textContent = open ? 'CLOSE' : 'MENU';
  });

  function stable(value) {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']';
    return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + stable(value[k])).join(',') + '}';
  }

  async function sha256Text(text) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  const short = (hash = '') => hash ? `${hash.slice(0, 12)}…${hash.slice(-12)}` : 'unavailable';

  function artifactHtml(items = []) {
    return items.map(a => `<div class="artifact"><b>${esc(a.format)} · ${esc(a.state || 'source')}</b><code>${esc(a.filename)}<br>SHA-256 ${esc(a.sha256)}</code></div>`).join('');
  }

  function paperCard(r) {
    return `<article class="paper-card">
      <div class="record-meta"><span class="record-badge ${r.status === 'canonical' ? 'canonical' : ''}">${esc(r.status)}</span><span>${esc(r.date)}</span><span>${esc(r.id)}</span></div>
      <h3>${esc(r.title)}</h3><p>${esc(r.summary)}</p>
      <p class="science"><strong>Evidence boundary:</strong> ${esc(r.scientific_status)}</p>
      <div class="artifact-list">${artifactHtml(r.artifacts || [])}</div>
      <code class="record-hash">record SHA-256 ${esc(r.record_sha256)}</code>
    </article>`;
  }

  function lineageCard(r) {
    return `<article class="lineage-record"><div class="record-meta"><span class="record-badge">${esc(r.status)}</span><span>${esc(r.date)}</span></div><h4>${esc(r.title)}</h4><p>${esc(r.summary)}</p><p><strong>Evidence:</strong> ${esc(r.scientific_status)}</p><code class="record-hash">${esc(r.record_sha256)}</code></article>`;
  }

  function deprecatedItems(r) {
    const titles = Array.isArray(r.whitepaper_titles) ? r.whitepaper_titles : [r.title];
    return titles.map((title, i) => `<div class="deprecated-item"><b>${esc(title)}</b><code>${esc(r.id)}.${String(i + 1).padStart(2, '0')} · grouped proof ${esc(short(r.record_sha256))}</code></div>`).join('');
  }

  async function verify(data) {
    const status = $('verification-status');
    const detail = $('verification-detail');
    status.className = 'verify-idle';
    status.textContent = 'VERIFYING…';
    const failures = [];
    for (const record of data.records) {
      const copy = structuredClone(record);
      const stored = copy.record_sha256;
      delete copy.record_sha256;
      const actual = await sha256Text(stable(copy));
      if (actual !== stored) failures.push(`${record.id} record digest mismatch`);
    }
    const material = [...data.records].sort((a,b) => a.id.localeCompare(b.id)).map(r => `${r.id}:${r.record_sha256}\n`).join('');
    const root = await sha256Text(material);
    if (root !== data.proof.root_sha256) failures.push('record-set root mismatch');
    if (failures.length) {
      status.className = 'verify-fail'; status.textContent = 'FAIL'; detail.textContent = failures.join(' · '); return false;
    }
    status.className = 'verify-pass'; status.textContent = 'PASS'; detail.textContent = `13 proof records verified locally. Root ${root}`; return true;
  }

  async function load() {
    const response = await fetch(REGISTRY_URL, {cache: 'no-store'});
    if (!response.ok) throw new Error(`registry HTTP ${response.status}`);
    const data = await response.json();
    $('metric-total').textContent = data.counts.listed_whitepapers;
    $('metric-materialized').textContent = data.counts.materialized;
    $('metric-active').textContent = data.counts.active;
    $('metric-legacy').textContent = data.counts.legacy;
    $('metric-deprecated').textContent = data.counts.deprecated_whitepapers;
    $('deprecated-count').textContent = `${data.counts.deprecated_whitepapers} papers · grouped proof record`;
    $('hero-root').textContent = data.proof.root_sha256;
    $('proof-root').textContent = data.proof.root_sha256;

    const materialized = data.records.filter(r => r.class === 'materialized');
    const active = data.records.filter(r => r.class === 'active');
    const legacy = data.records.filter(r => r.class === 'legacy');
    const deprecated = data.records.filter(r => r.class === 'deprecated');
    $('materialized-records').innerHTML = materialized.map(paperCard).join('');
    $('active-records').innerHTML = active.map(lineageCard).join('');
    $('legacy-records').innerHTML = legacy.map(lineageCard).join('');
    $('deprecated-records').innerHTML = deprecated.map(deprecatedItems).join('');

    if (data.proof.anchor_commit) {
      $('anchor-commit').textContent = data.proof.anchor_commit;
      for (const id of ['anchor-link','anchor-link-hero']) {
        const link = $(id); link.href = COMMIT_BASE + data.proof.anchor_commit; link.classList.remove('disabled'); link.removeAttribute('aria-disabled');
      }
    } else {
      $('anchor-commit').textContent = 'Anchor is created in the next Git commit.';
    }

    $('verify-registry').addEventListener('click', () => verify(data));
    $('copy-root').addEventListener('click', async () => {
      await navigator.clipboard.writeText(data.proof.root_sha256);
      $('copy-root').textContent = 'Copied'; setTimeout(() => $('copy-root').textContent = 'Copy root', 1200);
    });
  }

  load().catch(error => {
    console.error(error);
    const target = $('materialized-records');
    if (target) target.innerHTML = `<div class="error-box">Research registry failed to load: ${esc(error.message)}</div>`;
    if ($('verification-status')) { $('verification-status').className = 'verify-fail'; $('verification-status').textContent = 'REGISTRY LOAD FAILED'; }
  });
})();

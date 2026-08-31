(() => {
  'use strict';

  const USER = 'MASSIVEMAGNETICS';
  const MAX_PUBLIC_PAGES = 5;
  const DAY = 86_400_000;

  const $ = (id) => document.getElementById(id);
  const clamp = (n, min = 0, max = 100) => Math.max(min, Math.min(max, n));
  const escapeText = (value) => String(value ?? '');

  const CAPABILITY_RULES = {
    evidence: ['truth', 'proof', 'verify', 'verification', 'audit', 'evidence', 'provenance', 'govern', 'defensive'],
    intelligence: ['radar', 'monitor', 'research', 'intel', 'recon', 'search', 'analysis', 'worldmonitor'],
    portfolio: ['portfolio', 'repo', 'repository', 'completion', 'starpower', 'asset', 'launch-console', 'inventory'],
    execution: ['operator', 'orchestrator', 'agent', 'autonomous', 'runtime', 'executor', 'deploy', 'rcp', 'automation'],
    cognition: ['victor', 'cognition', 'agi', 'intelligence', 'llm', 'memory', 'brain', 'mind', 'reason'],
    audio: ['audio', 'music', 'song', 'suno', 'voice', 'ear', 'wav', 'bark'],
    vision: ['image', 'vision', 'video', 'visual', 'wan', 'roop', 'lip'],
    mobile: ['android', 'mobile', 'victoros', 'phone'],
    ip: ['patent', 'intellectual property', 'prior art', 'invention', 'mmip'],
    distribution: ['site', 'website', 'network', 'media', 'store', 'creator', 'broadcast', 'marketing', 'public'],
    commerce: ['commerce', 'checkout', 'stripe', 'store', 'pricing', 'revenue', 'income'],
    devtools: ['code', 'repo', 'github', 'builder', 'compiler', 'sdk', 'cli', 'developer', 'tooling']
  };

  const CANONICAL_OVERRIDES = {
    'massivemagnetics.github.io': ['intelligence', 'distribution', 'commerce', 'evidence', 'portfolio'],
    'truth-compiler-ai': ['evidence', 'devtools'],
    'starpower-core': ['portfolio', 'intelligence', 'execution', 'cognition', 'devtools'],
    'dev-ville': ['execution', 'evidence', 'devtools', 'cognition'],
    'victor-ssi': ['execution', 'cognition'],
    'victoros': ['mobile', 'cognition', 'execution'],
    'massivemagnetics-ip': ['ip', 'evidence', 'portfolio'],
    'the-ai-ear': ['audio', 'intelligence'],
    'sunokiller': ['audio', 'cognition'],
    'omni': ['audio', 'cognition', 'execution'],
    'worldmonitor': ['intelligence', 'distribution'],
    'complete-active-aware-repo-intelligence': ['portfolio', 'intelligence', 'devtools']
  };

  const FALLBACK_REPOS = [
    {name:'MASSIVEMAGNETICS.github.io',html_url:'https://github.com/MASSIVEMAGNETICS/MASSIVEMAGNETICS.github.io',size:1,description:'Public site, proof, commerce and Frontier Radar.',fork:false,archived:false,pushed_at:'2026-08-31T13:57:37Z',topics:[]},
    {name:'truth-compiler-ai',html_url:'https://github.com/MASSIVEMAGNETICS/truth-compiler-ai',size:50,description:'Evidence-bounded truth compiler.',fork:false,archived:false,pushed_at:'2026-08-24T00:00:00Z',topics:[]},
    {name:'starpower-core',html_url:'https://github.com/MASSIVEMAGNETICS/starpower-core',size:100,description:'Shared Completion Fabric and portfolio intelligence.',fork:false,archived:false,pushed_at:'2026-08-24T00:00:00Z',topics:[]},
    {name:'dev-ville',html_url:'https://github.com/MASSIVEMAGNETICS/dev-ville',size:529,description:'Governed Victor execution architecture and remediation control plane.',fork:false,archived:false,pushed_at:'2026-08-27T00:00:00Z',topics:[]},
    {name:'VICTOR-SSI',html_url:'https://github.com/MASSIVEMAGNETICS/VICTOR-SSI',size:100,description:'Bounded Victor Operator execution substrate.',fork:false,archived:false,pushed_at:'2026-08-24T00:00:00Z',topics:[]},
    {name:'victorOS',html_url:'https://github.com/MASSIVEMAGNETICS/victorOS',size:100,description:'Android client and local Victor interface.',fork:false,archived:false,pushed_at:'2026-08-24T00:00:00Z',topics:[]},
    {name:'MASSIVEMAGNETICS-IP',html_url:'https://github.com/MASSIVEMAGNETICS/MASSIVEMAGNETICS-IP',size:54,description:'IP custody, prior art and invention evidence ledger.',fork:false,archived:false,pushed_at:'2026-08-27T00:00:00Z',topics:[]},
    {name:'the-ai-ear',html_url:'https://github.com/MASSIVEMAGNETICS/the-ai-ear',size:180,description:'Audio analysis and machine listening.',fork:false,archived:false,pushed_at:'2026-08-20T00:00:00Z',topics:[]}
  ];

  const BLUEPRINTS = [
    {
      name: 'Convergence Engine',
      requirements: ['intelligence', 'portfolio', 'evidence', 'execution', 'distribution'],
      thesis: 'Continuously compare the external frontier with the internal repository estate, assemble high-leverage build candidates, expose every supporting repo and proof anchor, then stop at a human decision gate.'
    },
    {
      name: 'Proof-to-Product Compiler',
      requirements: ['portfolio', 'evidence', 'commerce', 'distribution'],
      thesis: 'Find technically real but commercially inert assets, verify what they actually do, and emit a bounded productization path with an existing checkout surface.'
    },
    {
      name: 'Sovereign R&D Autopilot',
      requirements: ['intelligence', 'cognition', 'execution', 'evidence'],
      thesis: 'Turn fresh public research signals into owner-controlled experiments with scoped execution and independent evidence before anything is promoted.'
    },
    {
      name: 'IP Discovery Engine',
      requirements: ['intelligence', 'portfolio', 'ip', 'evidence'],
      thesis: 'Detect recurring architecture patterns across the portfolio, connect them to dated evidence, and surface inventions that deserve prior-art review or protection.'
    },
    {
      name: 'Creative Signal Foundry',
      requirements: ['audio', 'cognition', 'distribution', 'evidence'],
      thesis: 'Connect audio generation, machine listening and owned distribution so creative experiments can be measured, compared and shipped without opaque cloud orchestration.'
    },
    {
      name: 'Mobile Sovereign Control Plane',
      requirements: ['mobile', 'cognition', 'execution', 'evidence'],
      thesis: 'Put bounded local commands, state and receipts on Android while keeping authority, verification and capability expansion explicit.'
    }
  ];

  function normalizeRepo(repo) {
    const topics = Array.isArray(repo.topics) ? repo.topics : [];
    const text = [repo.name, repo.description, repo.language, ...topics].filter(Boolean).join(' ').toLowerCase();
    const capabilities = new Set();
    for (const [capability, terms] of Object.entries(CAPABILITY_RULES)) {
      if (terms.some((term) => text.includes(term))) capabilities.add(capability);
    }
    const override = CANONICAL_OVERRIDES[String(repo.name || '').toLowerCase()] || [];
    override.forEach((capability) => capabilities.add(capability));
    return {...repo, topics, capabilities};
  }

  function daysSince(dateString) {
    const time = Date.parse(dateString || '');
    return Number.isFinite(time) ? Math.max(0, (Date.now() - time) / DAY) : 9999;
  }

  function readiness(repo, evidenceRepos) {
    let score = 8;
    if (!repo.fork) score += 18;
    if (repo.size > 0) score += 10;
    if (repo.size >= 50) score += 8;
    if (repo.size >= 500) score += 4;
    const age = daysSince(repo.pushed_at || repo.updated_at);
    if (age <= 30) score += 16;
    else if (age <= 90) score += 9;
    else if (age <= 365) score += 3;
    if (repo.description) score += 8;
    if (repo.topics.length) score += 4;
    if (repo.capabilities.size >= 2) score += 7;
    if (repo.capabilities.size >= 4) score += 5;
    if (evidenceRepos.has(repo.name.toLowerCase())) score += 22;
    if (repo.fork) score -= 26;
    if (repo.size === 0) score -= 26;
    if (repo.archived) score -= 35;
    return clamp(Math.round(score));
  }

  function repoClass(repo, evidenceRepos) {
    if (repo.archived) return 'archived';
    if (repo.fork) return 'fork/reference';
    if (repo.size === 0) return 'shell';
    if (evidenceRepos.has(repo.name.toLowerCase())) return 'verified core';
    const text = `${repo.name} ${repo.description || ''}`.toLowerCase();
    if (/test|playground|experiment|research|prototype|poc|demo/.test(text)) return 'research/prototype';
    if (repo.capabilities.size >= 2) return 'active system';
    return 'unclassified';
  }

  async function fetchJson(url) {
    const response = await fetch(url, {cache: 'no-store', headers: {'Accept': 'application/vnd.github+json'}});
    if (!response.ok) throw new Error(`${url} returned ${response.status}`);
    return response.json();
  }

  async function fetchPublicRepos() {
    const collected = [];
    for (let page = 1; page <= MAX_PUBLIC_PAGES; page += 1) {
      const batch = await fetchJson(`https://api.github.com/users/${USER}/repos?per_page=100&page=${page}&sort=updated&direction=desc`);
      if (!Array.isArray(batch)) throw new Error('GitHub repository response was not an array');
      collected.push(...batch);
      if (batch.length < 100) break;
    }
    const unique = new Map(collected.map((repo) => [repo.id || repo.full_name || repo.name, repo]));
    return [...unique.values()];
  }

  function evidenceRepoSet(ledger) {
    const repos = new Set();
    for (const entry of ledger?.entries || []) {
      for (const evidence of entry?.evidence || []) {
        const match = String(evidence?.url || '').match(/github\.com\/MASSIVEMAGNETICS\/([^/]+)/i);
        if (match) repos.add(match[1].toLowerCase());
      }
    }
    ['truth-compiler-ai','dev-ville','victor-ssi','starpower-core','victoros','massivemagnetics.github.io'].forEach((name) => repos.add(name));
    return repos;
  }

  function selectForCapability(repos, capability, used) {
    const candidates = repos
      .filter((repo) => repo.capabilities.has(capability))
      .sort((a, b) => b.readiness - a.readiness);
    return candidates.find((repo) => !used.has(repo.name.toLowerCase())) || candidates[0] || null;
  }

  function assembleBlueprint(blueprint, repos, evidenceRepos) {
    const used = new Set();
    const parts = [];
    let missing = 0;
    for (const capability of blueprint.requirements) {
      const repo = selectForCapability(repos, capability, used);
      if (!repo) {
        missing += 1;
        parts.push({capability, repo: null});
        continue;
      }
      used.add(repo.name.toLowerCase());
      parts.push({capability, repo});
    }
    const real = parts.filter((part) => part.repo);
    const avg = real.length ? real.reduce((sum, part) => sum + part.repo.readiness, 0) / real.length : 0;
    const verified = real.filter((part) => evidenceRepos.has(part.repo.name.toLowerCase())).length;
    const diversity = new Set(real.map((part) => part.repo.name.toLowerCase())).size;
    const score = clamp(Math.round(avg + verified * 3 + Math.min(diversity, 5) * 1.5 - missing * 24));
    return {...blueprint, parts, missing, score};
  }

  function clear(element) {
    while (element?.firstChild) element.removeChild(element.firstChild);
  }

  function chip(text, kind = '') {
    const span = document.createElement('span');
    span.className = `chip ${kind}`.trim();
    span.textContent = text;
    return span;
  }

  function renderCandidate(candidate, evidenceRepos) {
    $('candidateScore').textContent = String(candidate.score);
    const root = $('candidateContent');
    clear(root);

    const copy = document.createElement('div');
    copy.className = 'candidate-copy';
    const label = document.createElement('p');
    label.className = 'eyebrow';
    label.textContent = candidate.missing ? 'FRONTIER PROTOTYPE / GAPS VISIBLE' : 'FRONTIER PROTOTYPE / ASSEMBLABLE NOW';
    const title = document.createElement('h3');
    title.textContent = candidate.name;
    const thesis = document.createElement('p');
    thesis.textContent = candidate.thesis;
    const meta = document.createElement('div');
    meta.className = 'candidate-meta';
    meta.append(chip(`${candidate.parts.length - candidate.missing}/${candidate.parts.length} organs present`, candidate.missing ? 'warn' : 'good'));
    meta.append(chip('public metadata only'));
    meta.append(chip('human approval required'));
    copy.append(label, title, thesis, meta);

    const parts = document.createElement('div');
    parts.className = 'parts';
    for (const part of candidate.parts) {
      const card = document.createElement('article');
      card.className = 'part';
      if (!part.repo) {
        const header = document.createElement('header');
        const strong = document.createElement('strong');
        strong.textContent = `Missing: ${part.capability}`;
        const state = document.createElement('span');
        state.textContent = 'GAP';
        header.append(strong, state);
        const p = document.createElement('p');
        p.textContent = 'No public repository was confidently mapped to this required capability.';
        card.append(header, p);
      } else {
        const link = document.createElement('a');
        link.href = part.repo.html_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        const header = document.createElement('header');
        const strong = document.createElement('strong');
        strong.textContent = part.repo.name;
        const state = document.createElement('span');
        state.textContent = `${part.capability} · ${part.repo.readiness}`;
        header.append(strong, state);
        const p = document.createElement('p');
        p.textContent = evidenceRepos.has(part.repo.name.toLowerCase()) ? 'Public proof anchor found for this repository.' : (part.repo.description || 'Public repository metadata matched this role.');
        link.append(header, p);
        card.append(link);
      }
      parts.append(card);
    }
    root.append(copy, parts);
  }

  function renderClasses(repos) {
    const counts = new Map();
    for (const repo of repos) counts.set(repo.classification, (counts.get(repo.classification) || 0) + 1);
    const order = ['verified core','active system','research/prototype','fork/reference','shell','archived','unclassified'];
    const root = $('classGrid');
    clear(root);
    for (const name of order) {
      if (!counts.has(name)) continue;
      const article = document.createElement('article');
      article.className = 'class-card';
      const strong = document.createElement('strong');
      strong.textContent = counts.get(name);
      const span = document.createElement('span');
      span.textContent = name;
      article.append(strong, span);
      root.append(article);
    }
  }

  function renderCapabilities(repos) {
    const counts = Object.fromEntries(Object.keys(CAPABILITY_RULES).map((key) => [key, 0]));
    for (const repo of repos) for (const capability of repo.capabilities) counts[capability] = (counts[capability] || 0) + 1;
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const max = Math.max(1, ...sorted.map(([, count]) => count));
    const root = $('capabilityBars');
    clear(root);
    for (const [name, count] of sorted) {
      const row = document.createElement('div');
      row.className = 'cap-row';
      const label = document.createElement('label');
      label.textContent = name;
      const bar = document.createElement('div');
      bar.className = 'bar';
      const fill = document.createElement('i');
      fill.style.width = `${Math.max(2, (count / max) * 100)}%`;
      bar.append(fill);
      const value = document.createElement('b');
      value.textContent = String(count);
      row.append(label, bar, value);
      root.append(row);
    }
  }

  function renderAssemblies(assemblies) {
    const root = $('assemblyGrid');
    clear(root);
    assemblies.forEach((assembly, index) => {
      const article = document.createElement('article');
      article.className = `assembly ${index === 0 ? 'top' : ''}`.trim();
      const header = document.createElement('header');
      const h3 = document.createElement('h3');
      h3.textContent = assembly.name;
      const score = document.createElement('span');
      score.className = 'score';
      score.textContent = `${assembly.score}/100`;
      header.append(h3, score);
      const p = document.createElement('p');
      p.textContent = assembly.thesis;
      const parts = document.createElement('div');
      parts.className = 'parts-inline';
      for (const part of assembly.parts) parts.append(chip(part.repo ? `${part.capability}: ${part.repo.name}` : `${part.capability}: MISSING`, part.repo ? '' : 'warn'));
      article.append(header, p, parts);
      root.append(article);
    });
  }

  function renderProof(ledger, evidenceRepos) {
    const root = $('proofSummary');
    clear(root);
    const entries = ledger?.entries || [];
    const verified = entries.filter((entry) => entry.status === 'VERIFIED').length;
    const software = entries.filter((entry) => entry.category === 'software').length;
    [
      ['Bounded public ledger', `${entries.length} entries; ${verified} marked VERIFIED by the ledger's own declared methodology.`],
      ['Software anchors', `${software} software entries connect claims to public repositories, immutable commits, workflows or deployments.`],
      ['Repository coverage', `${evidenceRepos.size} repository names were extracted from GitHub evidence links and canonical anchors.`],
      ['Claim boundary', ledger?.methodology?.claim_boundary || 'Evidence must not be upgraded into a stronger claim.']
    ].forEach(([title, text]) => {
      const item = document.createElement('div');
      item.className = 'stack-item';
      const strong = document.createElement('strong');
      strong.textContent = title;
      const span = document.createElement('span');
      span.textContent = text;
      item.append(strong, span);
      root.append(item);
    });
  }

  function renderCommerce(audit, network, commerce) {
    const auditProducts = Array.isArray(audit?.products) ? audit.products : [];
    const musicSkus = Array.isArray(commerce?.catalog_skus) ? commerce.catalog_skus : [];
    const networkActive = network?.status === 'active' ? 1 : 0;
    const total = auditProducts.length + musicSkus.length + networkActive;
    $('offerCount').textContent = String(total);
    const root = $('commerceSummary');
    clear(root);
    const recurring = auditProducts.filter((item) => item.billing === 'monthly');
    const rows = [
      ['Truth Compiler / Proof Compiler', `${auditProducts.length} priced offers found in the active audit registry.`],
      ['Direct music', `${musicSkus.length} catalog SKUs are bound to the active commerce registry.`],
      ['B Heard Network', networkActive ? 'Creator Promotion registry is active with a Stripe checkout.' : 'Creator Promotion registry is not currently active.'],
      ['Recurring revenue surface', recurring.length ? `${recurring.length} monthly offer found: ${recurring.map((item) => `${item.name} $${item.price_usd}/mo`).join(', ')}.` : 'No recurring offer found in the loaded registry.']
    ];
    rows.forEach(([title, text]) => {
      const item = document.createElement('div');
      item.className = 'stack-item';
      const strong = document.createElement('strong');
      strong.textContent = title;
      const span = document.createElement('span');
      span.textContent = text;
      item.append(strong, span);
      root.append(item);
    });
  }

  function countFrontier(feed) {
    for (const key of ['items','signals','entries','results']) if (Array.isArray(feed?.[key])) return feed[key].length;
    return Array.isArray(feed) ? feed.length : 0;
  }

  function showError(error) {
    const root = $('candidateContent');
    clear(root);
    const card = document.createElement('div');
    card.className = 'error-card';
    card.textContent = `The live portfolio scan failed closed: ${escapeText(error.message)}. Reload to retry. No recommendation was manufactured.`;
    root.append(card);
    $('candidateScore').textContent = '—';
    $('liveState').textContent = 'FAILED CLOSED';
    $('liveState').className = 'live-pill partial';
  }

  async function compute() {
    $('liveState').textContent = 'SCANNING';
    $('liveState').className = 'live-pill';
    $('recomputeButton').disabled = true;

    try {
      const [ledgerResult, auditResult, networkResult, commerceResult, frontierResult, reposResult] = await Promise.allSettled([
        fetchJson('/proof/ledger.json'),
        fetchJson('/audit/offer.json'),
        fetchJson('/network/offer.json'),
        fetchJson('/store/commerce.json'),
        fetchJson('/frontier-radar/data/feed.json'),
        fetchPublicRepos()
      ]);

      if (ledgerResult.status !== 'fulfilled') throw ledgerResult.reason;
      const ledger = ledgerResult.value;
      const evidenceRepos = evidenceRepoSet(ledger);

      const liveRepos = reposResult.status === 'fulfilled' ? reposResult.value : FALLBACK_REPOS;
      const repos = liveRepos.map(normalizeRepo).map((repo) => ({
        ...repo,
        readiness: readiness(repo, evidenceRepos),
        classification: repoClass(repo, evidenceRepos)
      }));

      if (!repos.length) throw new Error('No public repositories were available to classify');

      const assemblies = BLUEPRINTS
        .map((blueprint) => assembleBlueprint(blueprint, repos, evidenceRepos))
        .sort((a, b) => b.score - a.score);

      $('repoCount').textContent = reposResult.status === 'fulfilled' ? String(repos.length) : `${repos.length}*`;
      $('proofCount').textContent = String((ledger.entries || []).length);
      $('frontierCount').textContent = frontierResult.status === 'fulfilled' ? String(countFrontier(frontierResult.value)) : '—';

      renderCandidate(assemblies[0], evidenceRepos);
      renderClasses(repos);
      renderCapabilities(repos);
      renderAssemblies(assemblies);
      renderProof(ledger, evidenceRepos);
      renderCommerce(
        auditResult.status === 'fulfilled' ? auditResult.value : {},
        networkResult.status === 'fulfilled' ? networkResult.value : {},
        commerceResult.status === 'fulfilled' ? commerceResult.value : {}
      );

      const partial = [reposResult, auditResult, networkResult, commerceResult, frontierResult].some((result) => result.status !== 'fulfilled');
      $('liveState').textContent = partial ? 'PARTIAL / BOUNDED' : 'LIVE / VERIFIED INPUTS';
      $('liveState').className = `live-pill ${partial ? 'partial' : 'ok'}`;
    } catch (error) {
      showError(error instanceof Error ? error : new Error(String(error)));
    } finally {
      $('recomputeButton').disabled = false;
    }
  }

  $('recomputeButton')?.addEventListener('click', compute);
  compute();
})();

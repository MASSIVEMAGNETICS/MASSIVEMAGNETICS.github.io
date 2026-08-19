(() => {
  'use strict';

  const MANIFEST_URL = '/.well-known/autopoiesis.json';
  const STATE_KEY = 'iambandobandz_autopoietic_state_v1';
  const DEFAULT_INTERVAL_MS = 300_000;
  const DEFAULT_TIMEOUT_MS = 5_000;

  let manifest = null;
  let timer = null;

  function readState() {
    try {
      return JSON.parse(localStorage.getItem(STATE_KEY) || '{}');
    } catch (_) {
      return {};
    }
  }

  function writeState(patch) {
    const next = {
      ...readState(),
      ...patch,
      updated_at: new Date().toISOString()
    };
    try {
      localStorage.setItem(STATE_KEY, JSON.stringify(next));
    } catch (_) {}
    window.dispatchEvent(new CustomEvent('iambandobandz:organism-state', { detail: next }));
    renderIndicator(next);
    return next;
  }

  function indicator() {
    let node = document.getElementById('autopoietic-status');
    if (node) return node;
    node = document.createElement('div');
    node.id = 'autopoietic-status';
    node.setAttribute('role', 'status');
    node.setAttribute('aria-live', 'polite');
    node.style.cssText = [
      'position:fixed',
      'right:12px',
      'bottom:12px',
      'z-index:2147483646',
      'font:700 10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace',
      'letter-spacing:.08em',
      'padding:8px 10px',
      'border:1px solid currentColor',
      'border-radius:999px',
      'background:rgba(8,8,8,.92)',
      'color:#9aa0a6',
      'box-shadow:0 4px 18px rgba(0,0,0,.35)',
      'pointer-events:none',
      'user-select:none'
    ].join(';');
    document.body.appendChild(node);
    return node;
  }

  function renderIndicator(state) {
    if (manifest?.runtime?.status_indicator === false) return;
    const node = indicator();
    const mode = String(state.mode || 'SENSING').toUpperCase();
    node.textContent = `SIGNAL ${mode}`;
    node.dataset.state = mode;
    if (mode === 'HEALTHY') node.style.color = '#39ff14';
    else if (mode === 'RECOVERED') node.style.color = '#ffd54a';
    else if (mode === 'OFFLINE') node.style.color = '#ff9d00';
    else if (mode === 'DEGRADED') node.style.color = '#ff4d6d';
    else node.style.color = '#9aa0a6';
  }

  async function fetchWithTimeout(url, timeoutMs) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, {
        cache: 'no-store',
        credentials: 'same-origin',
        signal: controller.signal,
        headers: { Accept: 'application/json' }
      });
    } finally {
      clearTimeout(timeout);
    }
  }

  function validateManifest(candidate) {
    if (!candidate || typeof candidate !== 'object') throw new Error('manifest-not-object');
    if (candidate.architecture !== 'bounded-autopoiesis-v1') throw new Error('architecture-mismatch');
    if (candidate.canonical_origin !== `${location.origin}/`) throw new Error('origin-mismatch');
    if (candidate.boundary?.same_origin_runtime !== true) throw new Error('boundary-mismatch');
    if (!Array.isArray(candidate.required_assets)) throw new Error('assets-missing');
    return candidate;
  }

  async function sense() {
    if (!navigator.onLine) {
      writeState({ mode: 'OFFLINE', reason: 'browser-offline' });
      return;
    }

    const timeoutMs = Number(manifest?.runtime?.health_timeout_ms) || DEFAULT_TIMEOUT_MS;
    try {
      const response = await fetchWithTimeout(`${MANIFEST_URL}?t=${Date.now()}`, timeoutMs);
      if (!response.ok) throw new Error(`manifest-http-${response.status}`);
      const candidate = validateManifest(await response.json());
      manifest = candidate;
      writeState({
        mode: 'HEALTHY',
        reason: 'canonical-manifest-verified',
        architecture: candidate.architecture,
        registry_version: candidate.registry_version || null,
        genome_sha256: candidate.proof?.genome_sha256 || null
      });
      schedule();
    } catch (error) {
      writeState({ mode: 'DEGRADED', reason: String(error?.message || error) });
    }
  }

  function schedule() {
    clearInterval(timer);
    const seconds = Number(manifest?.runtime?.health_interval_seconds);
    const intervalMs = Number.isFinite(seconds) && seconds >= 60
      ? seconds * 1000
      : DEFAULT_INTERVAL_MS;
    timer = setInterval(sense, intervalMs);
  }

  async function registerWorker() {
    if (!('serviceWorker' in navigator)) {
      writeState({ mode: 'DEGRADED', reason: 'service-worker-unsupported' });
      return;
    }
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      registration.update().catch(() => {});
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data?.type === 'LKG_SERVED') {
          writeState({
            mode: 'RECOVERED',
            reason: 'last-known-good-served',
            recovered_url: event.data.url || null
          });
        }
      });
    } catch (error) {
      writeState({ mode: 'DEGRADED', reason: `service-worker:${String(error?.message || error)}` });
    }
  }

  window.addEventListener('online', sense);
  window.addEventListener('offline', () => writeState({ mode: 'OFFLINE', reason: 'browser-offline' }));

  document.addEventListener('DOMContentLoaded', async () => {
    writeState({ mode: 'SENSING', reason: 'startup' });
    if (navigator.storage?.persist) {
      navigator.storage.persist().catch(() => {});
    }
    await registerWorker();
    await sense();
    schedule();
  });
})();

(() => {
  'use strict';

  const EVENT_KEY = 'iambandobandz_click_events';
  const SESSION_KEY = 'iambandobandz_session_id';
  const MAX_LOCAL_EVENTS = 2000;
  const musicHosts = ['spotify.com', 'music.apple.com', 'unitedmasters.com', 'audiomack.com'];

  function randomId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  }

  function sessionId() {
    let value = sessionStorage.getItem(SESSION_KEY);
    if (!value) {
      value = randomId();
      sessionStorage.setItem(SESSION_KEY, value);
    }
    return value;
  }

  function acquisition() {
    const query = new URLSearchParams(location.search);
    return {
      referrer: document.referrer || '',
      utm_source: query.get('utm_source') || '',
      utm_medium: query.get('utm_medium') || '',
      utm_campaign: query.get('utm_campaign') || ''
    };
  }

  function readLocal() {
    try {
      const parsed = JSON.parse(localStorage.getItem(EVENT_KEY) || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  }

  function writeLocal(events) {
    try {
      localStorage.setItem(EVENT_KEY, JSON.stringify(events.slice(-MAX_LOCAL_EVENTS)));
    } catch (_) {}
  }

  function collectorEndpoint() {
    return String(document.querySelector('meta[name="iambandobandz:analytics-endpoint"]')?.content || '').trim();
  }

  function sendRemote(payload) {
    const endpoint = collectorEndpoint();
    if (!endpoint || !endpoint.startsWith('https://')) return false;
    const body = JSON.stringify(payload);
    try {
      if (navigator.sendBeacon) {
        return navigator.sendBeacon(endpoint, new Blob([body], { type: 'application/json' }));
      }
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
        credentials: 'omit'
      }).catch(() => {});
      return true;
    } catch (_) {
      return false;
    }
  }

  function track(eventName, details = {}) {
    const payload = {
      event: String(eventName || 'unknown').slice(0, 80),
      session_id: sessionId(),
      page_path: location.pathname,
      ...acquisition(),
      ...details,
      timestamp: new Date().toISOString()
    };
    const events = readLocal();
    events.push(payload);
    writeLocal(events);
    sendRemote(payload);
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(payload);
    window.dispatchEvent(new CustomEvent('iambandobandz:analytics', { detail: payload }));
    return payload;
  }

  function classifyLink(link) {
    let url;
    try { url = new URL(link.href, location.href); } catch (_) { return null; }
    const isMusic = musicHosts.some((host) => url.hostname.includes(host));
    const isStripe = url.hostname === 'buy.stripe.com' || url.hostname === 'book.stripe.com';
    const isRevenue = Boolean(link.dataset.revenuePath) || isStripe;
    const label = (link.querySelector('h3')?.textContent || link.textContent || url.hostname)
      .trim().replace(/\s+/g, ' ').slice(0, 100);
    return {
      url,
      isMusic,
      isStripe,
      isRevenue,
      label,
      path: link.dataset.revenuePath || (isMusic ? 'music' : isStripe ? 'checkout' : url.origin === location.origin ? 'internal' : 'external')
    };
  }

  document.addEventListener('click', (event) => {
    const link = event.target.closest?.('a[href]');
    if (!link) return;
    const info = classifyLink(link);
    if (!info) return;
    const common = {
      label: info.label,
      destination: info.url.origin === location.origin ? info.url.pathname : info.url.hostname,
      path: info.path,
      stage: link.dataset.loopStage || (info.isStripe ? 'checkout' : 'outbound'),
      sku: link.dataset.sku || '',
      format: link.dataset.format || ''
    };
    if (info.isStripe) track('checkout_start', common);
    else if (info.isRevenue) track('revenue_path_click', common);
    else if (info.isMusic) track('track_button_click', common);
    else track('link_click', common);
  });

  window.IAMBandoAnalytics = {
    track,
    readLocal,
    status: () => ({
      mode: collectorEndpoint() ? 'site-wide-collector-configured' : 'local-browser-only',
      collector_endpoint_configured: Boolean(collectorEndpoint()),
      local_event_count: readLocal().length,
      session_id: sessionId()
    })
  };

  track('page_view');
})();

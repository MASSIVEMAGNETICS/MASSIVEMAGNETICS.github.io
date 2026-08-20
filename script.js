(() => {
  'use strict';

  const menuButton = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav-links');

  if (menuButton && nav) {
    menuButton.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.textContent = open ? 'CLOSE' : 'MENU';
    });
    nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
      nav.classList.remove('open');
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.textContent = 'MENU';
    }));
  }

  const analyticsKey = 'iambandobandz_click_events';
  const query = new URLSearchParams(location.search);
  const acquisition = {
    referrer: document.referrer || '',
    utm_source: query.get('utm_source') || '',
    utm_medium: query.get('utm_medium') || '',
    utm_campaign: query.get('utm_campaign') || ''
  };

  function track(eventName, details = {}) {
    const payload = {
      event: eventName,
      page_path: location.pathname,
      ...acquisition,
      ...details,
      timestamp: new Date().toISOString()
    };
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(payload);
    if (typeof window.gtag === 'function') window.gtag('event', eventName, details);
    if (typeof window.plausible === 'function') window.plausible(eventName, { props: details });
    if (window.umami?.track) window.umami.track(eventName, details);
    try {
      const events = JSON.parse(localStorage.getItem(analyticsKey) || '[]');
      events.push(payload);
      localStorage.setItem(analyticsKey, JSON.stringify(events.slice(-250)));
    } catch (_) {}
  }

  const leadApiEndpoint = String(
    document.querySelector('meta[name="iambandobandz:lead-api-endpoint"]')?.content || ''
  ).trim();
  const consentTextVersion = 'signal-capture-v1';

  function newIdempotencyKey() {
    if (window.crypto?.randomUUID) return `web-${window.crypto.randomUUID()}`;
    const random = window.crypto?.getRandomValues
      ? Array.from(window.crypto.getRandomValues(new Uint32Array(4)), (value) => value.toString(16)).join('')
      : Math.random().toString(36).slice(2) + Date.now().toString(36);
    return `web-${Date.now()}-${random}`;
  }

  async function submitFirstPartyLead({ email, phone, consent, idempotencyKey }) {
    if (!leadApiEndpoint) throw new Error('First-party lead API is disabled');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(leadApiEndpoint, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email,
          phone,
          sms_consent: consent,
          consent_text_version: consentTextVersion,
          source: 'website-engaged-music-capture',
          idempotency_key: idempotencyKey
        }),
        signal: controller.signal
      });
      if (!response.ok) throw new Error(`First-party capture failed: ${response.status}`);
      const receipt = await response.json();
      if (!receipt?.ok || !receipt?.receipt_id) throw new Error('First-party capture returned no receipt');
      return receipt;
    } finally {
      clearTimeout(timeout);
    }
  }

  async function submitFormSubmit(data) {
    const response = await fetch('https://formsubmit.co/ajax/bandobandz440@gmail.com', {
      method: 'POST',
      headers: { Accept: 'application/json' },
      body: data
    });
    if (!response.ok) throw new Error(`Fallback capture failed: ${response.status}`);
    return response.json().catch(() => ({}));
  }

  const modal = document.createElement('div');
  modal.className = 'capture-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-labelledby', 'capture-title');
  modal.innerHTML = `
    <div class="capture-card">
      <p class="eyebrow">Own the signal / no algorithm required</p>
      <h2 id="capture-title">GET THE NEXT DROP DIRECT.</h2>
      <p>Leave an email or mobile number, then continue to the music. No fake urgency. No sold data. Just releases, videos, and major transmissions.</p>
      <form id="signal-capture-form">
        <div class="capture-grid">
          <input type="email" name="email" autocomplete="email" placeholder="Email address" aria-label="Email address">
          <input type="tel" name="phone" autocomplete="tel" placeholder="Mobile number" aria-label="Mobile number">
        </div>
        <label class="consent"><input type="checkbox" name="sms_consent"><span>I agree to receive occasional automated promotional texts from IAMBANDOBANDZ. Consent is not a condition of purchase. Message and data rates may apply. Reply STOP to opt out.</span></label>
        <p class="consent-legal"><a href="/privacy/">Privacy</a> · <a href="/terms/">Terms</a></p>
        <input type="hidden" name="_subject" value="New IAMBANDOBANDZ Signal Signup">
        <input type="hidden" name="source" value="Website engaged-music capture">
        <div class="capture-actions">
          <button type="submit">JOIN + CONTINUE</button>
          <button class="skip-capture" type="button">SKIP TO MUSIC</button>
        </div>
        <p class="capture-status" aria-live="polite"></p>
      </form>
    </div>`;
  document.body.appendChild(modal);

  let pendingUrl = '';
  let pendingLabel = '';
  const form = modal.querySelector('form');
  const status = modal.querySelector('.capture-status');

  function continueToMusic() {
    modal.classList.remove('open');
    document.body.style.overflow = '';
    sessionStorage.setItem('signal_capture_seen', '1');
    if (pendingUrl) window.open(pendingUrl, '_blank', 'noopener,noreferrer');
    pendingUrl = '';
  }

  modal.querySelector('.skip-capture').addEventListener('click', () => {
    track('signal_capture_skipped', { destination: pendingLabel });
    continueToMusic();
  });

  modal.addEventListener('click', (event) => {
    if (event.target === modal) continueToMusic();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal.classList.contains('open')) continueToMusic();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const email = String(data.get('email') || '').trim();
    const phone = String(data.get('phone') || '').trim();
    const consent = data.get('sms_consent') === 'on';

    if (!email && !phone) {
      status.textContent = 'Enter an email or mobile number—or skip straight to the music.';
      return;
    }
    if (phone && !consent) {
      status.textContent = 'Check the SMS consent box to submit a mobile number.';
      return;
    }

    status.textContent = 'Locking in the signal…';
    const method = email && phone ? 'email_phone' : email ? 'email' : 'phone';
    const idempotencyKey = newIdempotencyKey();
    let provider = 'formsubmit';

    try {
      if (leadApiEndpoint) {
        try {
          const receipt = await submitFirstPartyLead({ email, phone, consent, idempotencyKey });
          provider = 'first_party';
          track('signal_capture_receipt', {
            provider,
            receipt: String(receipt.receipt_id).slice(0, 80),
            destination: pendingLabel
          });
        } catch (primaryError) {
          track('signal_capture_primary_error', { message: String(primaryError), destination: pendingLabel });
          await submitFormSubmit(data);
          provider = 'formsubmit_fallback';
        }
      } else {
        await submitFormSubmit(data);
      }

      track('signal_capture_complete', { method, provider, destination: pendingLabel });
      status.textContent = 'Signal locked. Redirecting…';
      setTimeout(continueToMusic, 450);
    } catch (error) {
      track('signal_capture_error', { message: String(error), provider, destination: pendingLabel });
      status.textContent = 'The capture relay failed, but the music won’t. Continuing…';
      setTimeout(continueToMusic, 900);
    }
  });

  const externalMusicHosts = ['spotify.com', 'music.apple.com', 'unitedmasters.com', 'audiomack.com'];
  const revenueHosts = ['iambandobandz.store', 'book.stripe.com'];
  const musicEngagementKey = 'signal_music_engagement_count';

  document.querySelectorAll('a[href]').forEach((link) => {
    link.addEventListener('click', (event) => {
      let url;
      try { url = new URL(link.href, location.href); } catch (_) { return; }
      const isMusic = externalMusicHosts.some((host) => url.hostname.includes(host));
      const isRevenue = revenueHosts.some((host) => url.hostname.includes(host)) || Boolean(link.dataset.revenuePath);
      const label = (link.querySelector('h3')?.textContent || link.textContent || url.hostname).trim().replace(/\s+/g, ' ').slice(0, 80);
      const funnelPath = link.dataset.revenuePath || (isMusic ? 'music' : url.origin === location.origin ? 'internal' : 'external');
      track(isRevenue ? 'revenue_path_click' : isMusic ? 'track_button_click' : 'link_click', {
        label,
        destination: url.origin === location.origin ? url.pathname : url.hostname,
        path: funnelPath,
        stage: link.dataset.loopStage || 'outbound'
      });

      if (!isMusic || sessionStorage.getItem('signal_capture_seen') === '1') return;
      const priorMusicEngagements = Number(sessionStorage.getItem(musicEngagementKey) || '0');
      sessionStorage.setItem(musicEngagementKey, String(priorMusicEngagements + 1));
      if (priorMusicEngagements < 1) return;

      event.preventDefault();
      pendingUrl = link.href;
      pendingLabel = label;
      modal.classList.add('open');
      document.body.style.overflow = 'hidden';
      setTimeout(() => modal.querySelector('input')?.focus(), 50);
    });
  });
})();
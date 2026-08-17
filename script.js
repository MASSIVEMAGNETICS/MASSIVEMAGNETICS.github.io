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
  function track(eventName, details = {}) {
    const payload = { event: eventName, ...details, path: location.pathname, timestamp: new Date().toISOString() };
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
        <input type="hidden" name="_subject" value="New IAMBANDOBANDZ Signal Signup">
        <input type="hidden" name="source" value="Website pre-redirect capture">
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
    try {
      const response = await fetch('https://formsubmit.co/ajax/bandobandz440@gmail.com', {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: data
      });
      if (!response.ok) throw new Error(`Capture failed: ${response.status}`);
      track('signal_capture_complete', { method: email && phone ? 'email_phone' : email ? 'email' : 'phone', destination: pendingLabel });
      status.textContent = 'Signal locked. Redirecting…';
      setTimeout(continueToMusic, 450);
    } catch (error) {
      track('signal_capture_error', { message: String(error) });
      status.textContent = 'The capture relay failed, but the music won’t. Continuing…';
      setTimeout(continueToMusic, 900);
    }
  });

  const externalMusicHosts = ['spotify.com', 'music.apple.com', 'unitedmasters.com', 'audiomack.com'];
  const revenueHosts = ['iambandobandz.store', 'book.stripe.com', 'facebook.com', 'github.com'];
  document.querySelectorAll('a[href^="http"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      let url;
      try { url = new URL(link.href); } catch (_) { return; }
      const isMusic = externalMusicHosts.some((host) => url.hostname.includes(host));
      const isRevenue = revenueHosts.some((host) => url.hostname.includes(host)) || link.dataset.revenuePath;
      const label = (link.querySelector('h3')?.textContent || link.textContent || url.hostname).trim().replace(/\s+/g, ' ').slice(0, 80);
      track(isRevenue ? 'revenue_path_click' : isMusic ? 'track_button_click' : 'external_link_click', { label, destination: url.hostname, path: link.dataset.revenuePath || 'music', stage: link.dataset.loopStage || 'outbound' });
      if (!isMusic || sessionStorage.getItem('signal_capture_seen') === '1') return;
      event.preventDefault();
      pendingUrl = link.href;
      pendingLabel = label;
      modal.classList.add('open');
      document.body.style.overflow = 'hidden';
      setTimeout(() => modal.querySelector('input')?.focus(), 50);
    });
  });
})();
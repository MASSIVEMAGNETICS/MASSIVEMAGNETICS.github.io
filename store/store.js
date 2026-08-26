(() => {
  'use strict';

  const ASSET_REGISTRY_URL = '/store/assets/assets.json';
  const COMMERCE_REGISTRY_URL = '/store/commerce.json';
  const FORMAT_ORDER = ['digital', 'cd', 'signed_cd'];
  const TOPIC_CHANNEL_ID = 'UCIaEOclqKUzIVPfkEuGzEEQ';
  const YOUTUBE_EMBED_ORIGIN = 'https://www.youtube-nocookie.com/embed/';

  function validCheckout(format) {
    if (!format || !format.checkout_url || !Number.isInteger(format.price_cents) || format.price_cents <= 0) {
      return false;
    }
    try {
      const url = new URL(format.checkout_url);
      return url.protocol === 'https:' && url.hostname === 'buy.stripe.com';
    } catch (_) {
      return false;
    }
  }

  function money(cents) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(cents / 100);
  }

  function attributedCheckoutUrl(format, sku, formatKey) {
    const url = new URL(format.checkout_url);
    url.searchParams.set('client_reference_id', sku);
    url.searchParams.set('utm_source', 'iambandobandz.com');
    url.searchParams.set('utm_medium', 'store');
    url.searchParams.set('utm_campaign', 'direct_store');
    url.searchParams.set('utm_content', formatKey);
    return url.toString();
  }

  function emitCheckoutStart(sku, formatKey, priceCents) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: 'checkout_start',
      funnel: 'direct-store',
      sku,
      format: formatKey,
      value: priceCents / 100,
      currency: 'USD',
    });
  }

  function buildCheckoutGrid(product, commerce) {
    const grid = document.createElement('div');
    grid.className = 'checkout-grid';
    grid.style.cssText = 'display:grid;gap:.45rem;';

    for (const formatKey of FORMAT_ORDER) {
      if (!product.formats.includes(formatKey)) continue;
      const format = commerce.formats[formatKey];
      if (!validCheckout(format)) continue;

      const link = document.createElement('a');
      link.className = 'buy-request';
      link.href = attributedCheckoutUrl(format, product.sku, formatKey);
      link.textContent = `${format.label} · ${money(format.price_cents)}`;
      link.dataset.checkout = 'active';
      link.dataset.format = formatKey;
      link.dataset.sku = product.sku;
      link.addEventListener('click', () => emitCheckoutStart(product.sku, formatKey, format.price_cents));
      grid.appendChild(link);
    }

    return grid.childElementCount ? grid : null;
  }

  function updateLiveCopy() {
    const status = document.querySelector('.store-status span');
    if (status) {
      status.textContent = 'Secure Stripe checkout active · digital $9.99 · CD $19.99 · signed CD $29.99 · U.S. shipping included on physical orders.';
    }

    const heroLead = document.querySelector('.hero-lead');
    if (heroLead) {
      heroLead.textContent = 'The IAMBANDOBANDZ catalog, direct from the source. Choose digital, CD, or signed CD and check out securely through Stripe.';
    }

    const catalogNote = document.querySelector('.catalog .section-heading > p:last-child');
    if (catalogNote) {
      catalogNote.textContent = 'Every checkout is bound to the canonical commerce registry and carries the selected release SKU into Stripe for reconciliation.';
    }
  }


  function validTopicPreview(product) {
    const preview = product && product.preview;
    return Boolean(
      preview &&
      preview.provider === 'youtube_topic' &&
      preview.channel_id === TOPIC_CHANNEL_ID &&
      /^[A-Za-z0-9_-]{11}$/.test(preview.video_id || '') &&
      /^OLAK5uy[A-Za-z0-9_-]+$/.test(preview.playlist_id || '')
    );
  }

  function previewEmbedUrl(preview) {
    const url = new URL(preview.video_id, YOUTUBE_EMBED_ORIGIN);
    url.searchParams.set('list', preview.playlist_id);
    url.searchParams.set('autoplay', '1');
    url.searchParams.set('mute', '1');
    url.searchParams.set('playsinline', '1');
    url.searchParams.set('rel', '0');
    return url.toString();
  }

  function installTopicPreview(card, product) {
    if (!validTopicPreview(product) || card.querySelector('.release-media')) return;

    const trigger = card.querySelector('.cover-link');
    if (!trigger) return;

    const preview = product.preview;
    const shell = document.createElement('div');
    shell.className = 'release-media';
    trigger.before(shell);
    shell.appendChild(trigger);
    trigger.classList.add('preview-trigger');
    trigger.href = preview.watch_url;
    trigger.dataset.youtubeVideo = preview.video_id;
    trigger.dataset.youtubePlaylist = preview.playlist_id;
    trigger.setAttribute('aria-label', `Preview ${product.title} from the IAMBANDOBANDZ Topic channel`);

    const badge = document.createElement('span');
    badge.className = 'preview-badge';
    badge.setAttribute('aria-hidden', 'true');
    badge.textContent = '▶ PREVIEW';
    trigger.appendChild(badge);

    let pinned = false;

    function unloadPreview(restoreFocus = false) {
      shell.querySelector('.youtube-preview')?.remove();
      shell.querySelector('.preview-close')?.remove();
      shell.removeAttribute('data-preview-active');
      shell.removeAttribute('data-preview-mode');
      pinned = false;
      if (restoreFocus) trigger.focus();
    }

    function loadPreview(mode) {
      if (shell.querySelector('.youtube-preview')) {
        if (mode === 'pinned') {
          pinned = true;
          shell.dataset.previewMode = 'pinned';
        }
        return;
      }

      const frame = document.createElement('iframe');
      frame.className = 'youtube-preview';
      frame.src = previewEmbedUrl(preview);
      frame.title = `${product.title} — IAMBANDOBANDZ Topic preview`;
      frame.loading = 'eager';
      frame.allow = 'autoplay; encrypted-media; picture-in-picture';
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      frame.allowFullscreen = true;

      const close = document.createElement('button');
      close.className = 'preview-close';
      close.type = 'button';
      close.textContent = 'Close preview';
      close.setAttribute('aria-label', `Close ${product.title} preview`);
      close.addEventListener('click', () => unloadPreview(true));

      shell.append(frame, close);
      shell.dataset.previewActive = 'true';
      shell.dataset.previewMode = mode;
      pinned = mode === 'pinned';
      if (pinned) close.focus();
    }

    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      loadPreview('pinned');
    });

    shell.addEventListener('pointerenter', () => {
      if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
        loadPreview('hover');
      }
    });

    shell.addEventListener('pointerleave', () => {
      if (!pinned) unloadPreview();
    });

    shell.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && shell.dataset.previewActive === 'true') {
        event.preventDefault();
        unloadPreview(true);
      }
    });
  }

  async function hydrateStore() {
    try {
      const [assetResponse, commerceResponse] = await Promise.all([
        fetch(ASSET_REGISTRY_URL, { cache: 'no-store' }),
        fetch(COMMERCE_REGISTRY_URL, { cache: 'no-store' }),
      ]);
      if (!assetResponse.ok) throw new Error(`asset registry ${assetResponse.status}`);
      if (!commerceResponse.ok) throw new Error(`commerce registry ${commerceResponse.status}`);

      const assets = await assetResponse.json();
      const commerce = await commerceResponse.json();
      if (!assets || assets.schema_version !== '1.0.0' || !Array.isArray(assets.products)) {
        throw new Error('unsupported storefront asset registry');
      }
      if (!commerce || commerce.schema_version !== '1.0.0' || commerce.status !== 'active' || !commerce.formats) {
        throw new Error('unsupported commerce registry');
      }

      document.documentElement.dataset.storeRegistry = assets.registry_version || 'unknown';
      document.documentElement.dataset.commerceRegistry = commerce.registry_version || 'unknown';
      const products = new Map(assets.products.map((product) => [product.sku, product]));

      document.querySelectorAll('.product-card[data-sku]').forEach((card) => {
        const product = products.get(card.dataset.sku);
        if (!product) {
          card.dataset.registryState = 'missing';
          return;
        }
        card.dataset.registryState = 'verified';
        installTopicPreview(card, product);

        const purchase = card.querySelector('.buy-request');
        if (!purchase) return;

        const checkoutGrid = buildCheckoutGrid(product, commerce);
        if (checkoutGrid) {
          purchase.replaceWith(checkoutGrid);
          card.dataset.checkoutState = 'active';
        } else {
          purchase.dataset.checkout = 'request-only';
          card.dataset.checkoutState = 'fallback';
        }
      });

      updateLiveCopy();
    } catch (error) {
      document.documentElement.dataset.commerceRegistry = 'unavailable';
      console.warn('Commerce registry unavailable; preserving request-only purchase flow.', error);
    }
  }

  hydrateStore();
})();

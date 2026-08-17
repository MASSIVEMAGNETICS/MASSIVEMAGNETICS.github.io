(() => {
  'use strict';

  const ASSET_REGISTRY_URL = '/store/assets/assets.json';
  const COMMERCE_REGISTRY_URL = '/store/commerce.json';
  const FORMAT_ORDER = ['digital', 'cd', 'signed_cd'];

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

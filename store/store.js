(() => {
  'use strict';

  const REGISTRY_URL = '/store/assets/assets.json';

  function validCheckout(product) {
    if (!product || product.checkout_state !== 'active' || !product.checkout_url) return false;
    try {
      const url = new URL(product.checkout_url, window.location.origin);
      return url.protocol === 'https:';
    } catch (_) {
      return false;
    }
  }

  async function hydrateStore() {
    try {
      const response = await fetch(REGISTRY_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error(`registry ${response.status}`);
      const registry = await response.json();
      if (!registry || registry.schema_version !== '1.0.0' || !Array.isArray(registry.products)) {
        throw new Error('unsupported storefront registry');
      }

      document.documentElement.dataset.storeRegistry = registry.registry_version || 'unknown';
      const products = new Map(registry.products.map((product) => [product.sku, product]));

      document.querySelectorAll('[data-sku]').forEach((card) => {
        const product = products.get(card.dataset.sku);
        if (!product) {
          card.dataset.registryState = 'missing';
          return;
        }
        card.dataset.registryState = 'verified';

        const purchase = card.querySelector('.buy-request');
        if (!purchase) return;

        if (validCheckout(product)) {
          purchase.href = product.checkout_url;
          purchase.textContent = 'BUY NOW ↗';
          purchase.target = '_blank';
          purchase.rel = 'noopener noreferrer';
          purchase.dataset.checkout = 'active';
        } else {
          purchase.dataset.checkout = 'request-only';
        }
      });
    } catch (error) {
      document.documentElement.dataset.storeRegistry = 'unavailable';
      console.warn('Store registry unavailable; preserving request-only purchase flow.', error);
    }
  }

  hydrateStore();
})();

(offerMarker => {
  'use strict';

  const OFFER_URL = '/catalog-recovery/offer.json';
  const status = document.getElementById('checkout-status');
  const action = document.getElementById('purchase-action');
  const price = document.getElementById('offer-price');
  const marker = offerMarker;

  const isStripePaymentLink = value => {
    try {
      const parsed = new URL(value);
      return parsed.protocol === 'https:' && ['buy.stripe.com', 'book.stripe.com'].includes(parsed.hostname);
    } catch (_error) {
      return false;
    }
  };

  fetch(OFFER_URL, { cache: 'no-store', credentials: 'same-origin' })
    .then(response => {
      if (!response.ok) throw new Error(`offer registry HTTP ${response.status}`);
      return response.json();
    })
    .then(offer => {
      if (offer.offer_code !== 'catalog_recovery_founding_79' || offer.price_cents !== 7900) {
        throw new Error('offer registry identity mismatch');
      }
      price.textContent = `$${(offer.price_cents / 100).toFixed(0)}`;
      const checkout = offer.checkout || {};
      if (offer.status === 'active' && checkout.status === 'active' && isStripePaymentLink(checkout.checkout_url)) {
        action.href = checkout.checkout_url;
        action.textContent = 'Buy securely — $79';
        action.dataset.loopStage = 'buy';
        action.dataset.checkout = 'stripe';
        status.textContent = 'Secure Stripe checkout active';
        status.classList.add('active');
        document.documentElement.dataset.catalogCheckout = 'active';
      } else {
        document.documentElement.dataset.catalogCheckout = marker;
      }
    })
    .catch(error => {
      document.documentElement.dataset.catalogCheckout = 'unavailable';
      console.warn('Catalog Recovery checkout remains request-only.', error);
    });
})('request-only');

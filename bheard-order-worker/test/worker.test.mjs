import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { verifyStripeSignature, extractIntake } from '../src/worker.mjs';

const secret = 'whsec_local_testing_only';
const stripeKey = 'sk_test_local_testing_only';
const paymentLink = 'plink_1U5HMjCpO4d12HbZcK2NQg5p';
const sessionId = 'cs_live_ABC123';
const session = {
  object: 'checkout.session', id: sessionId, livemode: true, status: 'complete',
  payment_status: 'paid', payment_link: paymentLink, currency: 'usd', amount_total: 999,
  metadata: { offer_code: 'bheard_creator_promo_v1' },
  custom_fields: [
    { key: 'artist_name', type: 'text', text: { value: 'Example Artist' } },
    { key: 'release_url', type: 'text', text: { value: 'https://example.org/release' } },
    { key: 'campaign_goal', type: 'dropdown', dropdown: { value: 'reach' } },
  ],
};
const event = { id: 'evt_ABC123', type: 'checkout.session.completed', livemode: true,
  data: { object: { object: 'checkout.session', id: sessionId } } };

async function signedHeader(raw, timestamp = Math.floor(Date.now() / 1000)) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const bytes = new Uint8Array(await crypto.subtle.sign('HMAC', key,
    new TextEncoder().encode(`${timestamp}.${raw}`)));
  return `t=${timestamp},v1=${[...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('')}`;
}
function db() {
  const orders = new Map(), events = new Map();
  return { orders, events,
    prepare(sql) { return { bind(...args) { return { sql, args }; } }; },
    async batch(statements) {
      const [order, evt] = statements;
      const created = !orders.has(order.args[0]);
      if (created) orders.set(order.args[0], order.args);
      if (!events.has(evt.args[0])) events.set(evt.args[0], evt.args);
      return [{ meta: { changes: Number(created) } }, { meta: { changes: 1 } }];
    },
  };
}
async function send({ ev = event, fetched = session, database = db(), header, raw, fetchError = false, testMode = false } = {}) {
  const payload = raw ?? JSON.stringify(ev);
  const signature = header ?? await signedHeader(payload);
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    assert.match(url, /^https:\/\/api\.stripe\.com\/v1\/checkout\/sessions\//);
    assert.equal(options.headers.authorization, `Bearer ${stripeKey}`);
    if (fetchError) return new Response('{}', { status: 503 });
    return Response.json(fetched);
  };
  try {
    const response = await worker.fetch(new Request('https://bheard.example/webhooks/stripe', {
      method: 'POST', headers: { 'stripe-signature': signature }, body: payload,
    }), { STRIPE_WEBHOOK_SECRET: secret, STRIPE_SECRET_KEY: stripeKey,
      BHEARD_PAYMENT_LINK_ID: paymentLink, BHEARD_EXPECT_LIVEMODE: testMode ? 'false' : 'true', DB: database });
    return { status: response.status, data: await response.json(), database };
  } finally { globalThis.fetch = original; }
}

test('valid signature and replay window', async () => {
  const raw = JSON.stringify(event);
  assert.equal(await verifyStripeSignature(raw, await signedHeader(raw), secret), true);
  assert.equal(await verifyStripeSignature(raw, await signedHeader(raw, Math.floor(Date.now()/1000)-301), secret), false);
  assert.equal(await verifyStripeSignature(raw, 't=100,v1=deadbeef', secret), false);
});
test('one paid session creates one order and repeated delivery does not duplicate it', async () => {
  const database = db();
  const first = await send({ database });
  const second = await send({ database });
  const third = await send({ database, ev: { ...event, id: 'evt_DEF456' } });
  assert.deepEqual([first.data.action, second.data.action, third.data.action],
    ['order_recorded', 'already_recorded', 'already_recorded']);
  assert.equal(database.orders.size, 1);
  assert.equal(database.events.size, 2);
  assert.equal(database.orders.get(sessionId)[5], 'paid_pending_fulfillment');
});
test('invalid signature cannot write an order', async () => {
  const database = db();
  const result = await send({ database, header: 't=9999999999,v1=' + '0'.repeat(64) });
  assert.equal(result.status, 400);
  assert.equal(database.orders.size, 0);
});
test('unpaid and unrelated link cannot become paid orders', async () => {
  const database = db();
  assert.equal((await send({ database, fetched: { ...session, payment_status: 'unpaid' } })).data.action, 'ignored_unpaid');
  assert.equal((await send({ database, fetched: { ...session, payment_link: 'plink_OTHER' } })).data.action, 'ignored_nonmatching_offer');
  assert.equal(database.orders.size, 0);
});
test('missing intake is persisted for manual repair, not marked fulfilled', async () => {
  const database = db();
  const incomplete = { ...session, custom_fields: [] };
  const result = await send({ database, fetched: incomplete });
  assert.equal(result.status, 200);
  assert.equal(database.orders.get(sessionId)[5], 'needs_intake');
});
test('Stripe retrieval outage yields retryable failure without writes', async () => {
  const database = db();
  const result = await send({ database, fetchError: true });
  assert.equal(result.status, 503);
  assert.equal(database.orders.size, 0);
});
test('invalid creator URL never marks order ready', () => {
  assert.equal(extractIntake({ custom_fields: [
    { key: 'artist_name', type: 'text', text: { value: 'A' } },
    { key: 'release_url', type: 'text', text: { value: 'file:///etc/passwd' } },
    { key: 'campaign_goal', type: 'dropdown', dropdown: { value: 'reach' } },
  ] }).state, 'needs_intake');
});
test('wrong event type is ignored', async () => {
  const database = db();
  const result = await send({ database, ev: { ...event, type: 'charge.succeeded' } });
  assert.equal(result.data.action, 'ignored_event_type');
  assert.equal(database.orders.size, 0);
});
test('ledger outage returns 503 for Stripe retry', async () => {
  const database = db(); database.batch = async () => { throw new Error('database_down'); };
  assert.equal((await send({ database })).status, 503);
});

test('isolated test-mode configuration accepts test events and rejects live events', async () => {
  const testEvent = { ...event, id: 'evt_TEST456', livemode: false, data: { object: { object: 'checkout.session', id: 'cs_test_ABC123' } } };
  const testSession = { ...session, id: 'cs_test_ABC123', livemode: false };
  const database = db();
  assert.equal((await send({ ev: testEvent, fetched: testSession, database, testMode: true })).data.action, 'order_recorded');
  assert.equal(database.orders.size, 1);
  assert.equal((await send({ database, testMode: true })).status, 400);
});

/** B Heard payment-to-order intake. No customer fulfillment or outbound messaging. */
const MAX_BODY_BYTES = 256 * 1024;
const MAX_AGE_SECONDS = 300;
const OFFER = 'bheard_creator_promo_v1';
const GOALS = new Set(['reach', 'review', 'traffic', 'awareness']);
const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
});

function bytesFromHex(value) {
  if (!/^[0-9a-f]{64}$/i.test(value)) return null;
  return Uint8Array.from(value.match(/.{2}/g), byte => parseInt(byte, 16));
}

export async function verifyStripeSignature(raw, header, secret, now = Date.now()) {
  if (!secret || !header || typeof header !== 'string') return false;
  const pairs = header.split(',').map(part => part.trim().split('='));
  const timestampText = pairs.find(([key]) => key === 't')?.[1];
  if (!/^\d{10,12}$/.test(timestampText || '')) return false;
  const timestamp = Number(timestampText);
  if (Math.abs(Math.floor(now / 1000) - timestamp) > MAX_AGE_SECONDS) return false;
  const signatures = pairs.filter(([key]) => key === 'v1').map(([, value]) => bytesFromHex(value)).filter(Boolean);
  if (!signatures.length) return false;
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']);
  const payload = new TextEncoder().encode(`${timestamp}.${raw}`);
  for (const signature of signatures) {
    if (await crypto.subtle.verify('HMAC', key, signature, payload)) return true;
  }
  return false;
}

function getCustomField(fields, key) {
  const field = Array.isArray(fields) ? fields.find(item => item?.key === key) : null;
  if (!field) return '';
  return String(field.type === 'dropdown' ? field.dropdown?.value || '' : field.text?.value || '').trim();
}

export function extractIntake(session) {
  const artist = getCustomField(session.custom_fields, 'artist_name').slice(0, 80);
  const release = getCustomField(session.custom_fields, 'release_url').slice(0, 200);
  const goal = getCustomField(session.custom_fields, 'campaign_goal');
  let validUrl = false;
  try {
    const url = new URL(release);
    const hostname = url.hostname.toLowerCase().replace(/\.$/, '');
    const localSuffixes = ['.localhost', '.local', '.internal', '.lan', '.home', '.test', '.invalid'];
    // Reject IP literals and local names before an order can be marked fulfillment-ready.
    // Any future network fetch must independently verify resolved IPs and redirect targets.
    validUrl = url.protocol === 'https:' && !url.username && !url.password &&
      hostname.includes('.') && !hostname.startsWith('[') &&
      !/^\d+\.\d+\.\d+\.\d+$/.test(hostname) &&
      !localSuffixes.some(suffix => hostname.endsWith(suffix));
  } catch { /* Invalid URLs are recorded for manual intake repair. */ }
  const valid = artist.length >= 1 && validUrl && GOALS.has(goal);
  return { artist, release, goal, state: valid ? 'paid_pending_fulfillment' : 'needs_intake' };
}

async function retrieveSession(sessionId, secret) {
  if (!/^cs_(live|test)_[A-Za-z0-9]+$/.test(sessionId)) throw new Error('invalid_session_id');
  const response = await fetch(`https://api.stripe.com/v1/checkout/sessions/${encodeURIComponent(sessionId)}`, {
    headers: { authorization: `Bearer ${secret}` }, signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new Error('stripe_session_unavailable');
  return response.json();
}

export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname !== '/webhooks/stripe') return json({ error: 'not_found' }, 404);
    if (request.method !== 'POST') return json({ error: 'method_not_allowed' }, 405);
    if (!env?.STRIPE_WEBHOOK_SECRET || !env?.STRIPE_SECRET_KEY || !env?.DB || !env?.BHEARD_PAYMENT_LINK_ID)
      return json({ error: 'service_unavailable' }, 503);
    let raw;
    try {
      const body = await request.arrayBuffer();
      if (body.byteLength > MAX_BODY_BYTES) return json({ error: 'payload_too_large' }, 413);
      raw = new TextDecoder('utf-8', { fatal: true }).decode(body);
    } catch { return json({ error: 'invalid_body' }, 400); }
    if (!(await verifyStripeSignature(raw, request.headers.get('stripe-signature'), env.STRIPE_WEBHOOK_SECRET)))
      return json({ error: 'invalid_signature' }, 400);
    let event;
    try { event = JSON.parse(raw); } catch { return json({ error: 'invalid_json' }, 400); }
    const expectedLive = env.BHEARD_EXPECT_LIVEMODE !== 'false';
    if (!event || typeof event.id !== 'string' || !/^evt_[A-Za-z0-9]+$/.test(event.id) || event.livemode !== expectedLive)
      return json({ error: 'invalid_event' }, 400);
    if (!['checkout.session.completed', 'checkout.session.async_payment_succeeded'].includes(event.type))
      return json({ received: true, action: 'ignored_event_type' });
    const eventSession = event.data?.object;
    if (eventSession?.object !== 'checkout.session' || typeof eventSession.id !== 'string')
      return json({ error: 'invalid_session' }, 400);
    let session;
    try { session = await retrieveSession(eventSession.id, env.STRIPE_SECRET_KEY); }
    catch { return json({ error: 'upstream_unavailable' }, 503); }
    if (session.id !== eventSession.id || session.livemode !== expectedLive ||
        session.payment_link !== env.BHEARD_PAYMENT_LINK_ID ||
        session.currency !== 'usd' || session.amount_total !== 999 ||
        session.metadata?.offer_code !== OFFER)
      return json({ received: true, action: 'ignored_nonmatching_offer' });
    if (session.status !== 'complete' || session.payment_status !== 'paid')
      return json({ received: true, action: 'ignored_unpaid' });
    const intake = extractIntake(session);
    try {
      // D1 batch is atomic. Unique session ID prevents double orders across distinct events.
      const result = await env.DB.batch([
        env.DB.prepare(`INSERT OR IGNORE INTO bheard_orders
          (stripe_session_id, stripe_event_id, artist_name, release_url, campaign_goal, status, amount_cents, currency)
          VALUES (?, ?, ?, ?, ?, ?, 999, 'usd')`).bind(
          session.id, event.id, intake.artist, intake.release, intake.goal, intake.state),
        env.DB.prepare(`INSERT OR IGNORE INTO bheard_webhook_events
          (stripe_event_id, stripe_session_id, event_type) VALUES (?, ?, ?)`).bind(
          event.id, session.id, event.type),
      ]);
      return json({ received: true, action: result?.[0]?.meta?.changes === 1 ? 'order_recorded' : 'already_recorded' });
    } catch {
      // Non-2xx response tells Stripe to retry rather than silently lose an order.
      return json({ error: 'ledger_unavailable' }, 503);
    }
  },
};

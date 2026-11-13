-- Apply before registering the live Stripe webhook. Never store card details.
CREATE TABLE IF NOT EXISTS bheard_orders (
  stripe_session_id TEXT PRIMARY KEY NOT NULL,
  stripe_event_id TEXT NOT NULL,
  artist_name TEXT NOT NULL,
  release_url TEXT NOT NULL,
  campaign_goal TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('paid_pending_fulfillment', 'needs_intake', 'in_progress', 'fulfilled', 'refunded')),
  amount_cents INTEGER NOT NULL CHECK (amount_cents = 999),
  currency TEXT NOT NULL CHECK (currency = 'usd'),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS bheard_webhook_events (
  stripe_event_id TEXT PRIMARY KEY NOT NULL,
  stripe_session_id TEXT NOT NULL REFERENCES bheard_orders(stripe_session_id),
  event_type TEXT NOT NULL,
  received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bheard_orders_status ON bheard_orders(status, created_at);

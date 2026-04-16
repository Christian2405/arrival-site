-- Promo codes table
CREATE TABLE IF NOT EXISTS promo_codes (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  code text UNIQUE NOT NULL,
  description text,
  discount_type text NOT NULL CHECK (discount_type IN ('percent_off', 'amount_off', 'free_months', 'extended_trial', 'seat_discount')),
  discount_value numeric NOT NULL,
  duration text DEFAULT 'once' CHECK (duration IN ('once', 'repeating', 'forever')),
  duration_months integer,
  applies_to text DEFAULT 'all' CHECK (applies_to IN ('pro', 'business', 'all')),
  max_uses integer,
  current_uses integer DEFAULT 0,
  expires_at timestamptz,
  stripe_coupon_id text,
  active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);

-- Track who redeemed what
CREATE TABLE IF NOT EXISTS promo_redemptions (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  promo_code_id uuid REFERENCES promo_codes(id),
  user_id uuid REFERENCES auth.users(id),
  redeemed_at timestamptz DEFAULT now()
);

-- RLS
ALTER TABLE promo_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE promo_redemptions ENABLE ROW LEVEL SECURITY;

-- Anyone can read promo codes (to validate)
CREATE POLICY "Anyone can read active promo codes" ON promo_codes FOR SELECT USING (active = true);

-- Users can read their own redemptions
CREATE POLICY "Users can read own redemptions" ON promo_redemptions FOR SELECT USING (auth.uid() = user_id);

-- Only service role can insert/update (via Netlify functions)
-- No insert/update policies needed for anon role

-- Index for fast code lookup
CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
CREATE INDEX IF NOT EXISTS idx_promo_redemptions_user ON promo_redemptions(user_id);

-- Insert some example codes (Christian can modify these)
INSERT INTO promo_codes (code, description, discount_type, discount_value, duration, applies_to) VALUES
  ('EARLYBIRD', '50% off first 3 months', 'percent_off', 50, 'repeating', 'all'),
  ('SFLAUNCH', '3 months free on Business', 'free_months', 3, 'once', 'business'),
  ('PARTNER100', '$100/seat instead of $200 forever', 'seat_discount', 100, 'forever', 'business');

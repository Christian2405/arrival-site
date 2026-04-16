const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'POST, OPTIONS'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  try {
    const authHeader = event.headers.authorization || '';
    const token = authHeader.replace('Bearer ', '');
    if (!token) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'No auth token' }) };
    }

    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Invalid token' }) };
    }

    const { code } = JSON.parse(event.body);
    if (!code) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Code required' }) };
    }

    // Look up the code
    const { data: promo, error: promoError } = await supabase
      .from('promo_codes')
      .select('*')
      .eq('code', code.toUpperCase().trim())
      .eq('active', true)
      .single();

    if (promoError || !promo) {
      return { statusCode: 404, headers, body: JSON.stringify({ error: 'Invalid promo code', valid: false }) };
    }

    // Check expiry
    if (promo.expires_at && new Date(promo.expires_at) < new Date()) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'This code has expired', valid: false }) };
    }

    // Check max uses
    if (promo.max_uses && promo.current_uses >= promo.max_uses) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'This code has reached its usage limit', valid: false }) };
    }

    // Check if user already redeemed
    const { data: existing } = await supabase
      .from('promo_redemptions')
      .select('id')
      .eq('promo_code_id', promo.id)
      .eq('user_id', user.id)
      .limit(1);

    if (existing && existing.length > 0) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'You have already used this code', valid: false }) };
    }

    // Build friendly description
    let discountLabel = '';
    switch (promo.discount_type) {
      case 'percent_off':
        discountLabel = promo.discount_value + '% off';
        if (promo.duration === 'repeating' && promo.duration_months) {
          discountLabel += ' for ' + promo.duration_months + ' months';
        } else if (promo.duration === 'forever') {
          discountLabel += ' forever';
        }
        break;
      case 'amount_off':
        discountLabel = '$' + promo.discount_value + ' off';
        break;
      case 'free_months':
        discountLabel = promo.discount_value + ' month' + (promo.discount_value > 1 ? 's' : '') + ' free';
        break;
      case 'extended_trial':
        discountLabel = promo.discount_value + '-day trial';
        break;
      case 'seat_discount':
        discountLabel = '$' + promo.discount_value + '/seat (instead of $200)';
        break;
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        valid: true,
        code: promo.code,
        description: promo.description || discountLabel,
        discount_type: promo.discount_type,
        discount_value: promo.discount_value,
        duration: promo.duration,
        duration_months: promo.duration_months,
        applies_to: promo.applies_to,
        stripe_coupon_id: promo.stripe_coupon_id
      })
    };

  } catch (err) {
    console.error('Validate promo error:', err);
    return { statusCode: 500, headers, body: JSON.stringify({ error: err.message }) };
  }
};

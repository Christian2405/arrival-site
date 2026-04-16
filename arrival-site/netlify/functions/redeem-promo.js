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

    // Find the promo code
    const { data: promo, error: promoError } = await supabase
      .from('promo_codes')
      .select('id, code, discount_type, discount_value, max_uses, current_uses')
      .eq('code', code.toUpperCase().trim())
      .eq('active', true)
      .single();

    if (promoError || !promo) {
      return { statusCode: 404, headers, body: JSON.stringify({ error: 'Code not found' }) };
    }

    // Record redemption
    const { error: redemptionError } = await supabase
      .from('promo_redemptions')
      .insert({
        promo_code_id: promo.id,
        user_id: user.id
      });

    if (redemptionError) {
      console.error('Redemption insert error:', redemptionError);
    }

    // Increment usage count
    const { error: updateError } = await supabase
      .from('promo_codes')
      .update({ current_uses: (promo.current_uses || 0) + 1 })
      .eq('id', promo.id);

    if (updateError) {
      console.error('Promo count update error:', updateError);
    }

    // Handle extended trial type (applies directly, no Stripe)
    if (promo.discount_type === 'extended_trial') {
      var trialEnd = new Date();
      trialEnd.setDate(trialEnd.getDate() + promo.discount_value);
      await supabase
        .from('subscriptions')
        .update({ trial_ends_at: trialEnd.toISOString() })
        .eq('user_id', user.id);
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ redeemed: true, discount_type: promo.discount_type, discount_value: promo.discount_value })
    };

  } catch (err) {
    console.error('Redeem promo error:', err);
    return { statusCode: 500, headers, body: JSON.stringify({ error: err.message }) };
  }
};

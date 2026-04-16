const Stripe = require('stripe');
const { createClient } = require('@supabase/supabase-js');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Stripe Price IDs
const PRICES = {
  pro: 'price_1T2wkcAO3BMpwX672CsLrhdQ',
  business_base: 'price_1T2wlnAO3BMpwX67HZQKSk6R',
  business_seat: 'price_1T2wmDAO3BMpwX67JSkM2fkF'
};

exports.handler = async (event) => {
  // CORS headers
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
    // Verify the user's Supabase JWT
    const authHeader = event.headers.authorization || '';
    const token = authHeader.replace('Bearer ', '');
    if (!token) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'No auth token' }) };
    }

    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Invalid token' }) };
    }

    const { plan, promoCode } = JSON.parse(event.body);
    if (!plan || !['pro', 'business'].includes(plan)) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid plan. Must be pro or business.' }) };
    }

    // Look up promo code if provided
    let promoDiscount = null;
    if (promoCode) {
      const { data: promo } = await supabase
        .from('promo_codes')
        .select('*')
        .eq('code', promoCode.toUpperCase().trim())
        .eq('active', true)
        .single();

      if (promo) {
        // Check plan compatibility
        if (promo.applies_to === 'all' || promo.applies_to === plan) {
          promoDiscount = promo;
        }
      }
    }

    // Check if user already has a Stripe customer ID
    const { data: sub } = await supabase
      .from('subscriptions')
      .select('stripe_customer_id')
      .eq('user_id', user.id)
      .limit(1)
      .single();

    let customerId = sub?.stripe_customer_id;

    // Create Stripe customer if needed
    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email,
        metadata: { supabase_user_id: user.id }
      });
      customerId = customer.id;

      // Store the customer ID
      await supabase
        .from('subscriptions')
        .update({ stripe_customer_id: customerId })
        .eq('user_id', user.id);
    }

    // Build line items based on plan
    let lineItems;
    if (plan === 'pro') {
      lineItems = [{ price: PRICES.pro, quantity: 1 }];
    } else {
      // Business: base plan (10 seats included)
      lineItems = [
        { price: PRICES.business_base, quantity: 1 }
      ];
    }

    // Determine the correct dashboard URL for redirect
    const origin = event.headers.origin || event.headers.referer?.replace(/\/[^/]*$/, '') || 'https://arrival-site.netlify.app';
    const dashboardPath = plan === 'business' ? '/dashboard-business' : '/dashboard-individual';

    // Build checkout session params
    const sessionParams = {
      customer: customerId,
      mode: 'subscription',
      line_items: lineItems,
      success_url: origin + dashboardPath + '?checkout=success',
      cancel_url: origin + dashboardPath,
      metadata: {
        supabase_user_id: user.id,
        plan: plan
      },
      subscription_data: {
        metadata: {
          supabase_user_id: user.id,
          plan: plan
        }
      }
    };

    // Apply promo code discount via Stripe
    if (promoDiscount) {
      if (promoDiscount.stripe_coupon_id) {
        // Use existing Stripe coupon
        sessionParams.discounts = [{ coupon: promoDiscount.stripe_coupon_id }];
      }
      if (promoDiscount.discount_type === 'free_months') {
        // Convert free months to trial days
        sessionParams.subscription_data.trial_period_days = Math.round(promoDiscount.discount_value * 30);
      }
      // Store promo code in metadata for redemption tracking
      sessionParams.metadata.promo_code = promoDiscount.code;
    }

    // Create Checkout Session
    const session = await stripe.checkout.sessions.create(sessionParams);

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ url: session.url })
    };
  } catch (err) {
    console.error('Checkout error:', err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: err.message })
    };
  }
};

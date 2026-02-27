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

    let parsedBody;
    try {
      parsedBody = JSON.parse(event.body);
    } catch (e) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON body' }) };
    }
    const { plan } = parsedBody;
    if (!plan || !['pro', 'business'].includes(plan)) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid plan. Must be pro or business.' }) };
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
      // Business: base plan only (10 seats included), extra seats added later
      lineItems = [
        { price: PRICES.business_base, quantity: 1 }
      ];
    }

    // Determine the correct dashboard URL for redirect
    const ALLOWED_ORIGINS = ['https://arrivalcompany.com', 'https://www.arrivalcompany.com'];
    const rawOrigin = event.headers.origin || event.headers.referer?.match(/^https?:\/\/[^/]+/)?.[0] || '';
    const origin = ALLOWED_ORIGINS.includes(rawOrigin) ? rawOrigin : 'https://arrivalcompany.com';
    const dashboardPath = plan === 'business' ? '/dashboard-business' : '/dashboard-individual';

    // Create Checkout Session
    const session = await stripe.checkout.sessions.create({
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
    });

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

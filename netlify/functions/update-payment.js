const Stripe = require('stripe');
const { createClient } = require('@supabase/supabase-js');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: 'Method not allowed' };
  }

  try {
    // Verify auth
    const token = event.headers.authorization?.replace('Bearer ', '');
    if (!token) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Unauthorized' }) };
    }

    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Invalid token' }) };
    }

    let body;
    try {
      body = JSON.parse(event.body);
    } catch (e) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON body' }) };
    }
    const { action } = body;

    // Get subscription
    const { data: sub } = await supabase
      .from('subscriptions')
      .select('stripe_customer_id, stripe_subscription_id')
      .eq('user_id', user.id)
      .single();

    if (!sub || !sub.stripe_customer_id) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'No billing account found' })
      };
    }

    // Action: create SetupIntent for new card
    if (action === 'create_setup_intent') {
      const setupIntent = await stripe.setupIntents.create({
        customer: sub.stripe_customer_id,
        payment_method_types: ['card'],
        usage: 'off_session'
      });

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          clientSecret: setupIntent.client_secret
        })
      };
    }

    // Action: confirm the new payment method is set as default
    if (action === 'set_default') {
      const { paymentMethodId } = body;

      if (!paymentMethodId) {
        return {
          statusCode: 400,
          headers,
          body: JSON.stringify({ error: 'Missing paymentMethodId' })
        };
      }

      // Set as customer default
      await stripe.customers.update(sub.stripe_customer_id, {
        invoice_settings: { default_payment_method: paymentMethodId }
      });

      // Also set as subscription default if subscription exists
      if (sub.stripe_subscription_id) {
        await stripe.subscriptions.update(sub.stripe_subscription_id, {
          default_payment_method: paymentMethodId
        });
      }

      // Get updated card info to return
      const pm = await stripe.paymentMethods.retrieve(paymentMethodId);
      const card = pm.card ? {
        brand: pm.card.brand,
        last4: pm.card.last4,
        expMonth: pm.card.exp_month,
        expYear: pm.card.exp_year
      } : null;

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ success: true, paymentMethod: card })
      };
    }

    return {
      statusCode: 400,
      headers,
      body: JSON.stringify({ error: 'Invalid action' })
    };

  } catch (err) {
    console.error('Update payment error:', err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: err.message })
    };
  }
};

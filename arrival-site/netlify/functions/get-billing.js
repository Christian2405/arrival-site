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

    // Get subscription with Stripe customer ID
    const { data: sub } = await supabase
      .from('subscriptions')
      .select('stripe_customer_id, stripe_subscription_id, plan, status, current_period_end')
      .eq('user_id', user.id)
      .single();

    if (!sub || !sub.stripe_customer_id) {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          plan: sub?.plan || 'pro',
          status: sub?.status || 'active',
          invoices: [],
          paymentMethod: null,
          currentPeriodEnd: null
        })
      };
    }

    // Fetch invoices from Stripe
    const invoices = await stripe.invoices.list({
      customer: sub.stripe_customer_id,
      limit: 10
    });

    const invoiceList = invoices.data.map(inv => ({
      id: inv.id,
      date: new Date(inv.created * 1000).toISOString(),
      amount: (inv.amount_paid / 100).toFixed(2),
      currency: inv.currency.toUpperCase(),
      status: inv.status,
      pdf: inv.invoice_pdf,
      number: inv.number
    }));

    // Fetch default payment method
    let paymentMethod = null;
    const customer = await stripe.customers.retrieve(sub.stripe_customer_id);

    if (customer.invoice_settings?.default_payment_method) {
      const pm = await stripe.paymentMethods.retrieve(
        customer.invoice_settings.default_payment_method
      );
      if (pm.card) {
        paymentMethod = {
          brand: pm.card.brand,
          last4: pm.card.last4,
          expMonth: pm.card.exp_month,
          expYear: pm.card.exp_year
        };
      }
    } else if (!customer.deleted) {
      // Try to get from subscription's default payment method
      if (sub.stripe_subscription_id) {
        const stripeSub = await stripe.subscriptions.retrieve(sub.stripe_subscription_id);
        if (stripeSub.default_payment_method) {
          const pm = await stripe.paymentMethods.retrieve(stripeSub.default_payment_method);
          if (pm.card) {
            paymentMethod = {
              brand: pm.card.brand,
              last4: pm.card.last4,
              expMonth: pm.card.exp_month,
              expYear: pm.card.exp_year
            };
          }
        }
      }
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        plan: sub.plan,
        status: sub.status,
        currentPeriodEnd: sub.current_period_end,
        invoices: invoiceList,
        paymentMethod: paymentMethod
      })
    };

  } catch (err) {
    console.error('Get billing error:', err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: err.message })
    };
  }
};

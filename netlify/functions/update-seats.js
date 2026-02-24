const Stripe = require('stripe');
const { createClient } = require('@supabase/supabase-js');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

const PRICE_BIZ_SEAT = 'price_1T2wmDAO3BMpwX67JSkM2fkF';

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
    // Verify auth
    const authHeader = event.headers.authorization || '';
    const token = authHeader.replace('Bearer ', '');
    if (!token) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'No auth token' }) };
    }

    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Invalid token' }) };
    }

    const { action, count } = JSON.parse(event.body);
    if (!action || !['add', 'remove'].includes(action)) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'action must be add or remove' }) };
    }

    const seatCount = parseInt(count, 10);
    if (!seatCount || seatCount < 1) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'count must be a positive integer' }) };
    }

    // Get subscription
    const { data: sub } = await supabase
      .from('subscriptions')
      .select('stripe_subscription_id, plan')
      .eq('user_id', user.id)
      .eq('status', 'active')
      .limit(1)
      .single();

    if (!sub || sub.plan !== 'business') {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Business subscription required' }) };
    }

    if (!sub.stripe_subscription_id) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'No Stripe subscription found' }) };
    }

    // Get the current subscription from Stripe
    const subscription = await stripe.subscriptions.retrieve(sub.stripe_subscription_id);

    // Find the seat line item
    const seatItem = subscription.items.data.find(
      item => item.price.id === PRICE_BIZ_SEAT
    );

    if (!seatItem) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Seat line item not found on subscription' }) };
    }

    const currentQuantity = seatItem.quantity || 0;
    let newQuantity;

    if (action === 'add') {
      newQuantity = currentQuantity + seatCount;
    } else {
      newQuantity = Math.max(0, currentQuantity - seatCount);

      // Validate: make sure we're not removing below active member count
      const { data: teamMember } = await supabase
        .from('team_members')
        .select('team_id')
        .eq('user_id', user.id)
        .eq('role', 'owner')
        .limit(1)
        .single();

      if (teamMember) {
        const { count: activeMembers } = await supabase
          .from('team_members')
          .select('*', { count: 'exact', head: true })
          .eq('team_id', teamMember.team_id)
          .in('status', ['active', 'invited']);

        const baseSeats = 10;
        const totalSeatsAfter = baseSeats + newQuantity;

        if (activeMembers > totalSeatsAfter) {
          return {
            statusCode: 400,
            headers,
            body: JSON.stringify({
              error: 'Cannot reduce below ' + activeMembers + ' seats (current active members). Remove team members first.'
            })
          };
        }
      }
    }

    // Update Stripe subscription
    await stripe.subscriptions.update(sub.stripe_subscription_id, {
      items: [{
        id: seatItem.id,
        quantity: newQuantity
      }],
      proration_behavior: 'create_prorations'
    });

    const newTotalSeats = 10 + newQuantity;

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        extraSeats: newQuantity,
        newSeatCount: newTotalSeats
      })
    };
  } catch (err) {
    console.error('Update seats error:', err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: err.message })
    };
  }
};

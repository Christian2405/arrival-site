const Stripe = require('stripe');
const { createClient } = require('@supabase/supabase-js');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Price IDs to identify plan type
const PRICE_PRO = 'price_1T2wkcAO3BMpwX672CsLrhdQ';
const PRICE_BIZ_BASE = 'price_1T2wlnAO3BMpwX67HZQKSk6R';
const PRICE_BIZ_SEAT = 'price_1T2wmDAO3BMpwX67JSkM2fkF';

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method not allowed' };
  }

  const sig = event.headers['stripe-signature'];
  let stripeEvent;

  try {
    stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    return { statusCode: 400, body: 'Webhook signature verification failed' };
  }

  console.log('Webhook event:', stripeEvent.type);

  try {
    switch (stripeEvent.type) {

      // ─── CHECKOUT COMPLETED ───────────────────────────
      case 'checkout.session.completed': {
        const session = stripeEvent.data.object;
        const userId = session.metadata?.supabase_user_id;
        const plan = session.metadata?.plan;

        if (!userId || !plan) {
          console.error('Missing metadata on checkout session');
          break;
        }

        // Update subscriptions table
        await supabase
          .from('subscriptions')
          .update({
            plan: plan,
            status: 'active',
            stripe_customer_id: session.customer,
            stripe_subscription_id: session.subscription
          })
          .eq('user_id', userId);

        // Update user account type
        await supabase
          .from('users')
          .update({ account_type: plan })
          .eq('id', userId);

        // For business plan: create team if needed
        if (plan === 'business') {
          // Check if user already has a team
          const { data: existingTeam } = await supabase
            .from('team_members')
            .select('team_id')
            .eq('user_id', userId)
            .eq('role', 'owner')
            .limit(1)
            .single();

          if (!existingTeam) {
            // Get user info for team name
            const { data: userInfo } = await supabase
              .from('users')
              .select('first_name, last_name, primary_trade')
              .eq('id', userId)
              .single();

            const teamName = (userInfo?.first_name || 'My') + "'s Team";

            // Create team
            const { data: newTeam } = await supabase
              .from('teams')
              .insert({
                name: teamName,
                owner_user_id: userId,
                trade: userInfo?.primary_trade || 'general_construction',
                max_seats: 10
              })
              .select('id')
              .single();

            if (newTeam) {
              // Add owner as team member
              await supabase
                .from('team_members')
                .insert({
                  team_id: newTeam.id,
                  user_id: userId,
                  email: (await supabase.auth.admin.getUserById(userId)).data?.user?.email,
                  role: 'owner',
                  status: 'active'
                });
            }
          }
        }

        console.log('Checkout completed: user=' + userId + ', plan=' + plan);
        break;
      }

      // ─── SUBSCRIPTION UPDATED ─────────────────────────
      case 'customer.subscription.updated': {
        const subscription = stripeEvent.data.object;
        const subId = subscription.id;

        // Find user by stripe_subscription_id
        const { data: sub } = await supabase
          .from('subscriptions')
          .select('user_id')
          .eq('stripe_subscription_id', subId)
          .limit(1)
          .single();

        if (!sub) {
          console.error('No subscription found for stripe_subscription_id:', subId);
          break;
        }

        // Map Stripe status to our status
        let status = 'active';
        if (subscription.status === 'past_due') status = 'past_due';
        if (subscription.status === 'canceled') status = 'canceled';
        if (subscription.status === 'unpaid') status = 'unpaid';

        // Update subscription status and period end
        const periodEnd = new Date(subscription.current_period_end * 1000).toISOString();
        await supabase
          .from('subscriptions')
          .update({
            status: status,
            current_period_end: periodEnd
          })
          .eq('stripe_subscription_id', subId);

        // Check for seat changes on business plan
        const seatItem = subscription.items?.data?.find(
          item => item.price.id === PRICE_BIZ_SEAT
        );

        if (seatItem !== undefined) {
          const extraSeats = seatItem.quantity || 0;
          const totalSeats = 10 + extraSeats;

          // Find user's team and update max_seats
          const { data: teamMember } = await supabase
            .from('team_members')
            .select('team_id')
            .eq('user_id', sub.user_id)
            .eq('role', 'owner')
            .limit(1)
            .single();

          if (teamMember) {
            await supabase
              .from('teams')
              .update({ max_seats: totalSeats })
              .eq('id', teamMember.team_id);
          }
        }

        console.log('Subscription updated: sub=' + subId + ', status=' + status);
        break;
      }

      // ─── SUBSCRIPTION DELETED (CANCELED) ──────────────
      case 'customer.subscription.deleted': {
        const subscription = stripeEvent.data.object;
        const subId = subscription.id;

        const { data: sub } = await supabase
          .from('subscriptions')
          .select('user_id')
          .eq('stripe_subscription_id', subId)
          .limit(1)
          .single();

        if (!sub) {
          console.error('No subscription found for deleted sub:', subId);
          break;
        }

        // Downgrade to free
        await supabase
          .from('subscriptions')
          .update({
            plan: 'free',
            status: 'canceled',
            stripe_subscription_id: null
          })
          .eq('stripe_subscription_id', subId);

        await supabase
          .from('users')
          .update({ account_type: 'free' })
          .eq('id', sub.user_id);

        console.log('Subscription canceled: user=' + sub.user_id);
        break;
      }

      // ─── PAYMENT FAILED ───────────────────────────────
      case 'invoice.payment_failed': {
        const invoice = stripeEvent.data.object;
        const customerId = invoice.customer;

        const { data: sub } = await supabase
          .from('subscriptions')
          .select('user_id')
          .eq('stripe_customer_id', customerId)
          .limit(1)
          .single();

        if (sub) {
          await supabase
            .from('subscriptions')
            .update({ status: 'past_due' })
            .eq('user_id', sub.user_id);

          console.log('Payment failed: user=' + sub.user_id);
        }
        break;
      }

      default:
        console.log('Unhandled event type:', stripeEvent.type);
    }
  } catch (err) {
    console.error('Webhook processing error:', err);
    // Still return 200 to prevent Stripe from retrying
  }

  return { statusCode: 200, body: JSON.stringify({ received: true }) };
};

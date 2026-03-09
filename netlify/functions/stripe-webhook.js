const Stripe = require('stripe');
const { createClient } = require('@supabase/supabase-js');
const { Resend } = require('resend');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);
const resend = new Resend(process.env.RESEND_API_KEY);

// Price IDs to identify plan type
const PRICE_PRO = 'price_1T2wkcAO3BMpwX672CsLrhdQ';
const PRICE_BIZ_BASE = 'price_1T2wlnAO3BMpwX67HZQKSk6R';
const PRICE_BIZ_SEAT = 'price_1T2wmDAO3BMpwX67JSkM2fkF';

const FROM_EMAIL = 'Arrival <noreply@arrivalcompany.com>';

function escapeHtml(str) { if (!str) return ''; return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

// ============================================
// EMAIL HELPER
// ============================================

function emailBase(content) {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><style>body{margin:0;padding:0;background:#f5f3ef;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}.wrapper{max-width:600px;margin:0 auto;padding:40px 20px}.card{background:#fff;border-radius:16px;padding:48px 40px;box-shadow:0 1px 3px rgba(0,0,0,.06)}.logo{font-family:Georgia,serif;font-size:28px;font-weight:700;color:#1a1a18;margin-bottom:32px;font-style:italic}h1{font-family:Georgia,serif;font-size:24px;font-weight:700;color:#1a1a18;margin:0 0 16px}p{font-size:15px;line-height:1.7;color:#4a4640;margin:0 0 16px}.btn{display:inline-block;background:#1a1a18;color:#fff!important;padding:14px 32px;border-radius:100px;text-decoration:none;font-size:15px;font-weight:600;margin:8px 0 24px}.highlight{background:#f5f3ef;border-radius:12px;padding:20px 24px;margin:20px 0}.highlight-label{font-size:13px;color:#7c736a;text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:4px}.highlight-value{font-size:20px;font-weight:700;color:#1a1a18}.divider{border:none;border-top:1px solid #e8e4df;margin:28px 0}.footer{text-align:center;padding:24px 0;font-size:13px;color:#7c736a}.footer a{color:#7c736a;text-decoration:underline}.feature-list{list-style:none;padding:0;margin:16px 0}.feature-list li{font-size:15px;color:#4a4640;padding:6px 0}.feature-list li::before{content:'✓';color:#4caf50;font-weight:700;margin-right:10px}</style></head><body><div class="wrapper"><div class="card"><div class="logo">arrival</div>${content}</div><div class="footer"><p>&copy; ${new Date().getFullYear()} Arrival — Your AI expert in the field.</p><p><a href="https://arrivalcompany.com">arrivalcompany.com</a></p></div></div></body></html>`;
}

async function sendEmail(to, subject, content) {
  try {
    const result = await resend.emails.send({
      from: FROM_EMAIL,
      to: to,
      subject: subject,
      html: emailBase(content)
    });
    console.log('Email sent to', to, ':', subject, result);
  } catch (err) {
    console.error('Email send error:', err);
    // Don't throw — email failure shouldn't break the webhook
  }
}

async function getUserInfo(userId) {
  const { data } = await supabase
    .from('users')
    .select('first_name, email')
    .eq('id', userId)
    .single();
  return data || {};
}

// ============================================
// WEBHOOK HANDLER
// ============================================

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

        // Upsert subscriptions table (handles case where no row exists yet)
        await supabase
          .from('subscriptions')
          .upsert({
            user_id: userId,
            plan: plan,
            status: 'active',
            stripe_customer_id: session.customer,
            stripe_subscription_id: session.subscription
          }, { onConflict: 'user_id' });

        // Update user account type
        await supabase
          .from('users')
          .update({ account_type: plan })
          .eq('id', userId);

        // For business plan: create team if needed
        if (plan === 'business') {
          const { data: existingTeam } = await supabase
            .from('teams')
            .select('id')
            .eq('owner_id', userId)
            .limit(1)
            .single();

          if (!existingTeam) {
            const { data: userInfo } = await supabase
              .from('users')
              .select('first_name, last_name, primary_trade')
              .eq('id', userId)
              .single();

            const teamName = (userInfo?.first_name || 'My') + "'s Team";

            const { data: newTeam, error: teamError } = await supabase
              .from('teams')
              .insert({
                name: teamName,
                owner_id: userId,
                primary_trade: userInfo?.primary_trade || 'general_construction',
                max_seats: 10
              })
              .select('id')
              .single();

            if (teamError) {
              console.error('Failed to create team:', teamError);
            }

            if (newTeam) {
              const userEmail = (await supabase.auth.admin.getUserById(userId)).data?.user?.email;
              const { error: memberError } = await supabase
                .from('team_members')
                .insert({
                  team_id: newTeam.id,
                  user_id: userId,
                  email: userEmail,
                  role: 'admin',
                  status: 'active'
                });

              if (memberError) {
                console.error('Failed to create team member:', memberError);
              } else {
                console.log('Team created:', newTeam.id, 'with owner:', userId);
              }
            }
          }
        }

        // 📧 Send subscription confirmed email
        const user = await getUserInfo(userId);
        if (user.email) {
          const planName = plan === 'business' ? 'Business' : 'Pro';
          const price = plan === 'business' ? '$200/month' : '$25/month';
          const dashUrl = plan === 'business'
            ? 'https://arrivalcompany.com/dashboard-business'
            : 'https://arrivalcompany.com/dashboard-individual';
          const features = plan === 'business'
            ? '<ul class="feature-list"><li>10 team seats included</li><li>Unlimited queries per seat</li><li>Shared team library</li><li>Admin dashboard &amp; analytics</li><li>Priority support + phone</li></ul>'
            : '<ul class="feature-list"><li>Unlimited AI queries</li><li>Unlimited camera snaps</li><li>Unlimited document uploads</li><li>Priority support</li><li>Early access to new features</li></ul>';

          await sendEmail(user.email, `You're now on ${planName}! 🎉`, `
            <h1>You're on the ${planName} plan!</h1>
            <p>Thanks for upgrading, ${escapeHtml(user.first_name) || 'there'}. Your subscription is now active and you have full access to all ${planName} features.</p>
            <div class="highlight">
              <div class="highlight-label">Your plan</div>
              <div class="highlight-value">${planName} &mdash; ${price}</div>
            </div>
            ${features}
            <a href="${dashUrl}" class="btn">Go to Dashboard</a>
            <hr class="divider">
            <p style="font-size:13px;color:#7c736a;">You can manage your subscription anytime from the Billing page in your dashboard.</p>
          `);
        }

        console.log('Checkout completed: user=' + userId + ', plan=' + plan);
        break;
      }

      // ─── SUBSCRIPTION UPDATED ─────────────────────────
      case 'customer.subscription.updated': {
        const subscription = stripeEvent.data.object;
        const subId = subscription.id;

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

        let status = 'active';
        if (subscription.cancel_at_period_end) status = 'cancel_at_period_end';
        if (subscription.status === 'past_due') status = 'past_due';
        if (subscription.status === 'canceled') status = 'cancelled';
        if (subscription.status === 'unpaid') status = 'cancelled';

        const periodEnd = new Date(subscription.current_period_end * 1000).toISOString();
        await supabase
          .from('subscriptions')
          .update({
            status: status,
            cancel_at_period_end: !!subscription.cancel_at_period_end,
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

          const { data: ownerTeam } = await supabase
            .from('teams')
            .select('id')
            .eq('owner_id', sub.user_id)
            .limit(1)
            .single();

          if (ownerTeam) {
            await supabase
              .from('teams')
              .update({ max_seats: totalSeats })
              .eq('id', ownerTeam.id);
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
            status: 'cancelled',
            stripe_subscription_id: null
          })
          .eq('stripe_subscription_id', subId);

        await supabase
          .from('users')
          .update({ account_type: 'free' })
          .eq('id', sub.user_id);

        // 📧 Send cancellation email
        const cancelUser = await getUserInfo(sub.user_id);
        if (cancelUser.email) {
          await sendEmail(cancelUser.email, 'Your subscription has been cancelled', `
            <h1>Subscription cancelled</h1>
            <p>Hi ${escapeHtml(cancelUser.first_name) || 'there'}, your paid subscription has ended and your account has been moved to the Free plan.</p>
            <p>You'll still have access to the free features — 10 queries per day, voice + text, and all trades.</p>
            <div class="highlight">
              <div class="highlight-label">Current plan</div>
              <div class="highlight-value">Free &mdash; $0/month</div>
            </div>
            <p>Changed your mind? You can upgrade again anytime.</p>
            <a href="https://arrivalcompany.com/dashboard-individual" class="btn">Re-subscribe</a>
            <hr class="divider">
            <p style="font-size:13px;color:#7c736a;">We'd love to know why you left. Reply to this email with any feedback.</p>
          `);
        }

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

          // 📧 Send payment failed email
          const failUser = await getUserInfo(sub.user_id);
          if (failUser.email) {
            await sendEmail(failUser.email, 'Payment failed — action required', `
              <h1>Payment failed</h1>
              <p>Hi ${escapeHtml(failUser.first_name) || 'there'}, we weren't able to process your latest payment. Your subscription is now past due.</p>
              <p>Please update your payment method to keep your access. If we can't collect payment, your account will be downgraded to the Free plan.</p>
              <a href="https://arrivalcompany.com/dashboard-individual" class="btn">Update Payment Method</a>
              <hr class="divider">
              <p style="font-size:13px;color:#7c736a;">If you believe this is a mistake, reply to this email and we'll help sort it out.</p>
            `);
          }

          console.log('Payment failed: user=' + sub.user_id);
        }
        break;
      }

      default:
        console.log('Unhandled event type:', stripeEvent.type);
    }
  } catch (err) {
    console.error('Webhook processing error:', err);
    return { statusCode: 500, body: JSON.stringify({ error: 'Webhook processing failed' }) };
  }

  return { statusCode: 200, body: JSON.stringify({ received: true }) };
};

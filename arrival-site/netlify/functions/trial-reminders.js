/**
 * Netlify Scheduled Function — Trial Reminders
 * Runs daily to:
 * 1. Send reminder emails 1 day before trial expires
 * 2. Expire trials and send expiry emails when trial_ends_at has passed
 */

const { schedule } = require("@netlify/functions");
const { createClient } = require("@supabase/supabase-js");
const { Resend } = require("resend");

// We import the email templates inline since Netlify bundles each function separately
const resend = new Resend(process.env.RESEND_API_KEY);
const FROM_EMAIL = 'Arrival <noreply@arrivalcompany.com>';

const supabase = createClient(
  process.env.SUPABASE_URL || 'https://nmmmrujtfrxrmajuggki.supabase.co',
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

function baseTemplate(content) {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>body{margin:0;padding:0;background:#f5f3ef;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}.wrapper{max-width:600px;margin:0 auto;padding:40px 20px}.card{background:#fff;border-radius:16px;padding:48px 40px;box-shadow:0 1px 3px rgba(0,0,0,0.06)}.logo{font-family:Georgia,serif;font-size:28px;font-weight:700;color:#1a1a18;margin-bottom:32px;font-style:italic}h1{font-family:Georgia,serif;font-size:24px;font-weight:700;color:#1a1a18;margin:0 0 16px}p{font-size:15px;line-height:1.7;color:#4a4640;margin:0 0 16px}.btn{display:inline-block;background:#1a1a18;color:#fff!important;padding:14px 32px;border-radius:100px;text-decoration:none;font-size:15px;font-weight:600;margin:8px 0 24px}.highlight{background:#f5f3ef;border-radius:12px;padding:20px 24px;margin:20px 0}.highlight-label{font-size:13px;color:#7c736a;text-transform:uppercase;letter-spacing:0.5px;font-weight:600;margin-bottom:4px}.highlight-value{font-size:20px;font-weight:700;color:#1a1a18}.divider{border:none;border-top:1px solid #e8e4df;margin:28px 0}.footer{text-align:center;padding:24px 0;font-size:13px;color:#7c736a}.feature-list{list-style:none;padding:0;margin:16px 0}.feature-list li{font-size:15px;color:#4a4640;padding:6px 0}.feature-list li::before{content:'✓';color:#4caf50;font-weight:700;margin-right:10px}</style></head><body><div class="wrapper"><div class="card"><div class="logo">arrival</div>${content}</div><div class="footer"><p>&copy; ${new Date().getFullYear()} Arrival — Your AI expert in the field.</p></div></div></body></html>`;
}

module.exports.handler = schedule("@daily", async (event) => {
  console.log("[trial-reminders] Running daily trial check...");

  try {
    // Get all active free subscriptions with trial dates
    const { data: subs, error } = await supabase
      .from('subscriptions')
      .select('id, user_id, trial_ends_at')
      .eq('plan', 'free')
      .eq('status', 'active')
      .not('trial_ends_at', 'is', null);

    if (error) {
      console.error("[trial-reminders] Query error:", error);
      return { statusCode: 500 };
    }

    if (!subs || subs.length === 0) {
      console.log("[trial-reminders] No active free trials found.");
      return { statusCode: 200 };
    }

    const now = new Date();

    for (const sub of subs) {
      const trialEnd = new Date(sub.trial_ends_at);
      const hoursLeft = (trialEnd - now) / (1000 * 60 * 60);

      // Get user info
      const { data: user } = await supabase
        .from('users')
        .select('email, first_name')
        .eq('id', sub.user_id)
        .single();

      if (!user || !user.email) continue;

      if (hoursLeft <= 0) {
        // Trial has expired — send expiry email and update status
        console.log(`[trial-reminders] Expiring trial for ${user.email}`);

        await supabase
          .from('subscriptions')
          .update({ status: 'trial_expired' })
          .eq('id', sub.id);

        await resend.emails.send({
          from: FROM_EMAIL,
          to: user.email,
          subject: 'Your free trial has ended',
          html: baseTemplate(`
            <h1>Your trial has ended</h1>
            <p>Hi ${user.first_name || 'there'}, your 7-day free trial of Arrival has expired. Your account is now locked.</p>
            <p>Upgrade to Pro or Business to get back in and keep using your AI assistant on job sites.</p>
            <a href="https://arrivalcompany.com/dashboard-individual#billing" class="btn">Upgrade Now</a>
            <hr class="divider">
            <p style="font-size:13px; color:#7c736a;">Miss us already? Reply to this email — we'd love to hear from you.</p>
          `)
        });

      } else if (hoursLeft > 0 && hoursLeft <= 24) {
        // 1 day left — send reminder
        console.log(`[trial-reminders] Sending 1-day reminder to ${user.email}`);

        await resend.emails.send({
          from: FROM_EMAIL,
          to: user.email,
          subject: 'Your free trial ends tomorrow ⏱',
          html: baseTemplate(`
            <h1>Your trial ends tomorrow</h1>
            <p>Hi ${user.first_name || 'there'}, your 7-day free trial of Arrival ends tomorrow. After that, you'll lose access to the dashboard and AI assistant.</p>
            <p>Upgrade now to keep using Arrival without interruption.</p>
            <div class="highlight">
              <div class="highlight-label">Recommended</div>
              <div class="highlight-value">Pro — $25/month</div>
            </div>
            <a href="https://arrivalcompany.com/dashboard-individual#billing" class="btn">Upgrade Now</a>
          `)
        });
      }
    }

    console.log(`[trial-reminders] Processed ${subs.length} subscriptions.`);
    return { statusCode: 200 };

  } catch (err) {
    console.error("[trial-reminders] Error:", err);
    return { statusCode: 500 };
  }
});

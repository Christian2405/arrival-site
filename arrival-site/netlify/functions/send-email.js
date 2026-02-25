const { Resend } = require('resend');

const resend = new Resend(process.env.RESEND_API_KEY);

const FROM_EMAIL = 'Arrival <noreply@arrivalcompany.com>';

// ============================================
// EMAIL TEMPLATES
// ============================================

function baseTemplate(content) {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 0; background: #f5f3ef; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    .wrapper { max-width: 600px; margin: 0 auto; padding: 40px 20px; }
    .card { background: #ffffff; border-radius: 16px; padding: 48px 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    .logo { font-family: Georgia, serif; font-size: 28px; font-weight: 700; color: #1a1a18; margin-bottom: 32px; font-style: italic; }
    h1 { font-family: Georgia, serif; font-size: 24px; font-weight: 700; color: #1a1a18; margin: 0 0 16px; }
    p { font-size: 15px; line-height: 1.7; color: #4a4640; margin: 0 0 16px; }
    .btn { display: inline-block; background: #1a1a18; color: #ffffff !important; padding: 14px 32px; border-radius: 100px; text-decoration: none; font-size: 15px; font-weight: 600; margin: 8px 0 24px; }
    .btn:hover { background: #333; }
    .highlight { background: #f5f3ef; border-radius: 12px; padding: 20px 24px; margin: 20px 0; }
    .highlight-label { font-size: 13px; color: #7c736a; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 4px; }
    .highlight-value { font-size: 20px; font-weight: 700; color: #1a1a18; }
    .divider { border: none; border-top: 1px solid #e8e4df; margin: 28px 0; }
    .footer { text-align: center; padding: 24px 0; font-size: 13px; color: #7c736a; }
    .footer a { color: #7c736a; text-decoration: underline; }
    .feature-list { list-style: none; padding: 0; margin: 16px 0; }
    .feature-list li { font-size: 15px; color: #4a4640; padding: 6px 0; }
    .feature-list li::before { content: '✓'; color: #4caf50; font-weight: 700; margin-right: 10px; }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="card">
      <div class="logo">arrival</div>
      ${content}
    </div>
    <div class="footer">
      <p>&copy; ${new Date().getFullYear()} Arrival &mdash; Your AI expert in the field.</p>
      <p><a href="https://arrivalcompany.com">arrivalcompany.com</a></p>
    </div>
  </div>
</body>
</html>`;
}

// ─── WELCOME ─────────────────────────────────
function welcomeEmail(firstName) {
  const name = firstName || 'there';
  return {
    subject: 'Welcome to Arrival! 👷',
    html: baseTemplate(`
      <h1>Welcome to Arrival, ${name}!</h1>
      <p>You're all set. Arrival is your AI expert in the field — ask questions by voice or text, snap photos of equipment for instant diagnostics, and upload your manuals for personalised answers.</p>
      <hr class="divider">
      <p><strong>Here's what you can do on the Free plan:</strong></p>
      <ul class="feature-list">
        <li>10 AI queries per day</li>
        <li>5 camera snaps per day</li>
        <li>Voice + text input</li>
        <li>All trades supported</li>
      </ul>
      <p>Want unlimited access? Upgrade to Pro for just $25/month.</p>
      <a href="https://arrivalcompany.com/dashboard-individual" class="btn">Go to Dashboard</a>
      <p style="font-size:13px; color:#7c736a;">Need help? Just reply to this email.</p>
    `)
  };
}

// ─── SUBSCRIPTION CONFIRMED ──────────────────
function subscriptionConfirmedEmail(firstName, plan) {
  const name = firstName || 'there';
  const planName = plan === 'business' ? 'Business' : 'Pro';
  const price = plan === 'business' ? '$250/month' : '$25/month';
  const dashboardUrl = plan === 'business'
    ? 'https://arrivalcompany.com/dashboard-business'
    : 'https://arrivalcompany.com/dashboard-individual';

  const features = plan === 'business'
    ? `<ul class="feature-list">
        <li>10 team seats included</li>
        <li>Unlimited queries per seat</li>
        <li>Shared team library</li>
        <li>Admin dashboard &amp; analytics</li>
        <li>Priority support + phone</li>
      </ul>`
    : `<ul class="feature-list">
        <li>Unlimited AI queries</li>
        <li>Unlimited camera snaps</li>
        <li>Unlimited document uploads</li>
        <li>Priority support</li>
        <li>Early access to new features</li>
      </ul>`;

  return {
    subject: `You're now on ${planName}! 🎉`,
    html: baseTemplate(`
      <h1>You're on the ${planName} plan!</h1>
      <p>Thanks for upgrading, ${name}. Your subscription is now active and you have full access to all ${planName} features.</p>
      <div class="highlight">
        <div class="highlight-label">Your plan</div>
        <div class="highlight-value">${planName} &mdash; ${price}</div>
      </div>
      ${features}
      <a href="${dashboardUrl}" class="btn">Go to Dashboard</a>
      <hr class="divider">
      <p style="font-size:13px; color:#7c736a;">You can manage your subscription anytime from the Billing page in your dashboard.</p>
    `)
  };
}

// ─── SUBSCRIPTION CANCELLED ──────────────────
function subscriptionCancelledEmail(firstName) {
  const name = firstName || 'there';
  return {
    subject: 'Your subscription has been cancelled',
    html: baseTemplate(`
      <h1>Subscription cancelled</h1>
      <p>Hi ${name}, your paid subscription has ended and your account has been moved to the Free plan.</p>
      <p>You'll still have access to the free features — 10 queries per day, voice + text, and all trades.</p>
      <div class="highlight">
        <div class="highlight-label">Current plan</div>
        <div class="highlight-value">Free &mdash; $0/month</div>
      </div>
      <p>Changed your mind? You can upgrade again anytime.</p>
      <a href="https://arrivalcompany.com/dashboard-individual" class="btn">Re-subscribe</a>
      <hr class="divider">
      <p style="font-size:13px; color:#7c736a;">We'd love to know why you left. Reply to this email with any feedback.</p>
    `)
  };
}

// ─── PAYMENT FAILED ──────────────────────────
function paymentFailedEmail(firstName) {
  const name = firstName || 'there';
  return {
    subject: 'Payment failed — action required',
    html: baseTemplate(`
      <h1>Payment failed</h1>
      <p>Hi ${name}, we weren't able to process your latest payment. Your subscription is now past due.</p>
      <p>Please update your payment method to keep your access. If we can't collect payment, your account will be downgraded to the Free plan.</p>
      <a href="https://arrivalcompany.com/dashboard-individual" class="btn">Update Payment Method</a>
      <hr class="divider">
      <p style="font-size:13px; color:#7c736a;">If you believe this is a mistake, reply to this email and we'll help sort it out.</p>
    `)
  };
}

// ─── TRIAL ENDING TOMORROW ──────────────────
function trialEndingTomorrowEmail(firstName) {
  const name = firstName || 'there';
  return {
    subject: 'Your free trial ends tomorrow ⏱',
    html: baseTemplate(`
      <h1>Your trial ends tomorrow</h1>
      <p>Hi ${name}, your 7-day free trial of Arrival ends tomorrow. After that, you'll lose access to the dashboard and AI assistant.</p>
      <p>Upgrade now to keep using Arrival without interruption.</p>
      <div class="highlight">
        <div class="highlight-label">Recommended</div>
        <div class="highlight-value">Pro &mdash; $25/month</div>
      </div>
      <ul class="feature-list">
        <li>Unlimited AI queries</li>
        <li>Unlimited camera snaps</li>
        <li>Up to 50 document uploads</li>
        <li>Chat history &amp; saved answers</li>
      </ul>
      <a href="https://arrivalcompany.com/dashboard-individual#billing" class="btn">Upgrade Now</a>
      <hr class="divider">
      <p style="font-size:13px; color:#7c736a;">If you have any questions, just reply to this email.</p>
    `)
  };
}

// ─── TRIAL EXPIRED ──────────────────────────
function trialExpiredEmail(firstName) {
  const name = firstName || 'there';
  return {
    subject: 'Your free trial has ended',
    html: baseTemplate(`
      <h1>Your trial has ended</h1>
      <p>Hi ${name}, your 7-day free trial of Arrival has expired. Your account is now locked.</p>
      <p>Upgrade to Pro or Business to get back in and keep using your AI assistant on job sites.</p>
      <a href="https://arrivalcompany.com/dashboard-individual#billing" class="btn">Upgrade Now</a>
      <hr class="divider">
      <p style="font-size:13px; color:#7c736a;">Miss us already? Reply to this email — we'd love to hear from you.</p>
    `)
  };
}

// ============================================
// TEMPLATE REGISTRY
// ============================================

const TEMPLATES = {
  welcome: welcomeEmail,
  subscription_confirmed: subscriptionConfirmedEmail,
  subscription_cancelled: subscriptionCancelledEmail,
  payment_failed: paymentFailedEmail,
  trial_ending_tomorrow: trialEndingTomorrowEmail,
  trial_expired: trialExpiredEmail
};

// ============================================
// SEND EMAIL HELPER (used by other functions)
// ============================================

async function sendEmail(to, templateName, templateArgs) {
  const templateFn = TEMPLATES[templateName];
  if (!templateFn) {
    throw new Error('Unknown email template: ' + templateName);
  }

  const { subject, html } = templateFn(...(templateArgs || []));

  const result = await resend.emails.send({
    from: FROM_EMAIL,
    to: to,
    subject: subject,
    html: html
  });

  console.log('Email sent:', templateName, 'to:', to, 'result:', JSON.stringify(result));
  return result;
}

// ============================================
// NETLIFY FUNCTION HANDLER (for client-side calls)
// ============================================

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method not allowed' };
  }

  try {
    const body = JSON.parse(event.body);
    const { to, template, args } = body;

    if (!to || !template) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Missing to or template' })
      };
    }

    const result = await sendEmail(to, template, args || []);

    return {
      statusCode: 200,
      body: JSON.stringify({ success: true, id: result.data?.id })
    };
  } catch (err) {
    console.error('Send email error:', err);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: err.message })
    };
  }
};

// Export sendEmail for use by other functions
exports.sendEmail = sendEmail;

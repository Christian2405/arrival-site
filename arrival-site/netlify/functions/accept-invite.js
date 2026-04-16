const { createClient } = require('@supabase/supabase-js');

// Use service role key to bypass RLS
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
    // Verify the user's auth token
    const authHeader = event.headers.authorization || '';
    const token = authHeader.replace('Bearer ', '');
    if (!token) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'No auth token' }) };
    }

    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Invalid token' }) };
    }

    const { email } = JSON.parse(event.body);
    if (!email) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Email required' }) };
    }

    // Verify the email matches the authenticated user
    if (user.email.toLowerCase() !== email.toLowerCase()) {
      return { statusCode: 403, headers, body: JSON.stringify({ error: 'Email mismatch' }) };
    }

    // Find the pending invite (bypasses RLS with service role)
    const { data: invites, error: inviteError } = await supabase
      .from('team_members')
      .select('id, team_id')
      .eq('email', email.toLowerCase())
      .eq('status', 'invited')
      .limit(1);

    if (inviteError) {
      console.error('Invite lookup error:', inviteError);
      return { statusCode: 500, headers, body: JSON.stringify({ error: 'Failed to look up invite' }) };
    }

    if (!invites || invites.length === 0) {
      return { statusCode: 404, headers, body: JSON.stringify({ error: 'No pending invite found', accepted: false }) };
    }

    const invite = invites[0];

    // Accept the invite — link user to team
    const { error: updateError } = await supabase
      .from('team_members')
      .update({
        user_id: user.id,
        status: 'active',
        joined_at: new Date().toISOString()
      })
      .eq('id', invite.id);

    if (updateError) {
      console.error('Team member update error:', updateError);
      return { statusCode: 500, headers, body: JSON.stringify({ error: 'Failed to accept invite' }) };
    }

    // Update subscription to business
    const { error: subError } = await supabase
      .from('subscriptions')
      .upsert({
        user_id: user.id,
        plan: 'business',
        status: 'active'
      }, { onConflict: 'user_id' });

    if (subError) {
      console.error('Subscription update error:', subError);
    }

    // Update user account type
    const { error: userError } = await supabase
      .from('users')
      .update({ account_type: 'business' })
      .eq('id', user.id);

    if (userError) {
      console.error('User update error:', userError);
    }

    console.log('Invite accepted:', email, '-> team', invite.team_id);

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ accepted: true, teamId: invite.team_id })
    };

  } catch (err) {
    console.error('Accept invite error:', err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: err.message })
    };
  }
};

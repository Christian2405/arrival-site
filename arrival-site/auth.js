// ============================================
// ARRIVAL AUTH - auth.js
// Supabase authentication for static HTML site
// ============================================

// --- CONFIGURATION ---
const SUPABASE_URL = 'https://nmmmrujtfrxrmajuggki.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tbW1ydWp0ZnJ4cm1hanVnZ2tpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1Mjk4NzEsImV4cCI6MjA4NzEwNTg3MX0.XaOQaqN_vbYSBeYFol63OzQFuKQYJ_pLXhMX7bvLAJQ';

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: { lock: function(_name, _acquireTimeout, fn) { return fn(); } }
});

// --- DEV MODE ---
const IS_DEV = ['localhost', '127.0.0.1', ''].includes(window.location.hostname);

// Store reference to original showPage
const _originalShowPage = window.showPage;

// ============================================
// UTILITY FUNCTIONS
// ============================================

function showFormError(elementId, message) {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.style.display = 'block';
}

function clearFormError(elementId) {
    const el = document.getElementById(elementId);
    el.textContent = '';
    el.style.display = 'none';
}

function showFormSuccess(elementId, message) {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.style.display = 'block';
}

function setButtonLoading(buttonId, loading) {
    const btn = document.getElementById(buttonId);
    const textEl = btn.querySelector('.btn-text');
    const loadingEl = btn.querySelector('.btn-loading');
    btn.disabled = loading;
    textEl.style.display = loading ? 'none' : 'inline';
    loadingEl.style.display = loading ? 'inline-flex' : 'none';
}

function showToast(message, type) {
    type = type || 'success';
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 4000);
}

// ============================================
// NAV STATE
// ============================================

function updateNavForAuth(user) {
    var loginLink = document.getElementById('nav-login-link');
    var signupLink = document.getElementById('nav-signup-link');
    var dashboardLink = document.getElementById('nav-dashboard-link');
    var logoutLink = document.getElementById('nav-logout-link');

    if (user) {
        loginLink.style.display = 'none';
        signupLink.style.display = 'none';
        dashboardLink.style.display = '';
        logoutLink.style.display = '';
    } else {
        loginLink.style.display = '';
        signupLink.style.display = '';
        dashboardLink.style.display = 'none';
        logoutLink.style.display = 'none';
    }
}

// ============================================
// SIGNUP
// ============================================

async function handleSignup(event) {
    event.preventDefault();
    clearFormError('signup-error');

    var firstName = document.getElementById('signup-first-name').value.trim();
    var lastName = document.getElementById('signup-last-name').value.trim();
    var email = document.getElementById('signup-email').value.trim();
    var password = document.getElementById('signup-password').value;
    var trade = document.getElementById('signup-trade').value;
    var experience = document.getElementById('signup-experience').value;
    var terms = document.getElementById('signup-terms').checked;

    if (!terms) {
        showFormError('signup-error', 'Please agree to the terms of service.');
        return;
    }
    if (password.length < 6) {
        showFormError('signup-error', 'Password must be at least 6 characters.');
        return;
    }

    setButtonLoading('signup-submit', true);

    try {
        // 1. Create auth user
        var result = await sb.auth.signUp({
            email: email,
            password: password,
            options: {
                data: { first_name: firstName, last_name: lastName }
            }
        });
        if (result.error) throw result.error;

        // Check if email confirmation is required
        if (!result.data.session) {
            showFormSuccess('signup-error', 'Check your email to confirm your account, then sign in.');
            setButtonLoading('signup-submit', false);
            return;
        }

        var userId = result.data.user.id;

        // 2. Insert user profile
        var userResult = await sb.from('users').insert({
            id: userId,
            email: email,
            first_name: firstName,
            last_name: lastName,
            primary_trade: trade,
            experience_level: experience,
            account_type: 'free'
        });
        if (userResult.error) throw userResult.error;

        // 3. Insert free subscription with 7-day trial
        var trialEnd = new Date();
        trialEnd.setDate(trialEnd.getDate() + 7);
        var subResult = await sb.from('subscriptions').insert({
            user_id: userId,
            plan: 'free',
            status: 'active',
            trial_ends_at: trialEnd.toISOString()
        });
        if (subResult.error) throw subResult.error;

        // 4. Send welcome email (fire-and-forget)
        fetch('/.netlify/functions/send-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ to: email, template: 'welcome', args: [firstName] })
        }).catch(function(err) { console.error('Welcome email error:', err); });

        // 5. Redirect to individual dashboard
        window.location.href = '/dashboard-individual';

    } catch (error) {
        console.error('Signup error:', error);
        var message = 'Something went wrong. Please try again.';
        if (error.message && error.message.includes('already registered')) {
            message = 'This email is already registered. Try signing in instead.';
        } else if (error.message) {
            message = error.message;
        }
        showFormError('signup-error', message);
    } finally {
        setButtonLoading('signup-submit', false);
    }
}

// ============================================
// LOGIN
// ============================================

async function handleLogin(event) {
    event.preventDefault();
    clearFormError('login-error');

    var email = document.getElementById('login-email').value.trim();
    var password = document.getElementById('login-password').value;

    if (!email || !password) {
        showFormError('login-error', 'Please enter your email and password.');
        return;
    }

    setButtonLoading('login-submit', true);

    try {
        var result = await sb.auth.signInWithPassword({ email: email, password: password });
        if (result.error) throw result.error;

        var userId = result.data.user.id;

        // Check user plan — free users always go to individual
        var profileResult = await sb.from('users').select('account_type').eq('id', userId).single();
        var accountType = profileResult.data ? profileResult.data.account_type : 'free';

        if (accountType === 'free') {
            localStorage.setItem('arrival_dashboard', 'individual');
            window.location.href = '/dashboard-individual';
        } else {
            // Check if user has an active team membership
            var tmResult = await sb
                .from('team_members')
                .select('team_id')
                .eq('user_id', userId)
                .eq('status', 'active')
                .limit(1);

            if (tmResult.data && tmResult.data.length > 0) {
                localStorage.setItem('arrival_dashboard', 'business');
                window.location.href = '/dashboard-business';
            } else {
                localStorage.setItem('arrival_dashboard', 'individual');
                window.location.href = '/dashboard-individual';
            }
        }

    } catch (error) {
        console.error('Login error:', error);
        var message = 'Invalid email or password.';
        if (error.message && error.message.includes('Email not confirmed')) {
            message = 'Please check your email to confirm your account.';
        }
        showFormError('login-error', message);
    } finally {
        setButtonLoading('login-submit', false);
    }
}

// ============================================
// PASSWORD RESET
// ============================================

async function handlePasswordResetRequest(event) {
    event.preventDefault();
    clearFormError('reset-error');

    var email = document.getElementById('reset-email').value.trim();
    if (!email) {
        showFormError('reset-error', 'Please enter your email address.');
        return;
    }

    setButtonLoading('reset-submit', true);

    try {
        var result = await sb.auth.resetPasswordForEmail(email, {
            redirectTo: window.location.origin + '/#type=recovery'
        });
        if (result.error) throw result.error;

        showFormSuccess('reset-success', 'Check your email for a password reset link. You can close this page.');
        document.getElementById('reset-submit').style.display = 'none';

    } catch (error) {
        showFormError('reset-error', error.message || 'Failed to send reset email. Please try again.');
    } finally {
        setButtonLoading('reset-submit', false);
    }
}

async function handlePasswordUpdate(event) {
    event.preventDefault();
    clearFormError('reset-update-error');

    var newPassword = document.getElementById('reset-new-password').value;
    var confirmPassword = document.getElementById('reset-confirm-password').value;

    if (newPassword !== confirmPassword) {
        showFormError('reset-update-error', 'Passwords do not match.');
        return;
    }
    if (newPassword.length < 6) {
        showFormError('reset-update-error', 'Password must be at least 6 characters.');
        return;
    }

    setButtonLoading('reset-update-submit', true);

    try {
        var result = await sb.auth.updateUser({ password: newPassword });
        if (result.error) throw result.error;

        showToast('Password updated successfully!');
        if (typeof _originalShowPage === 'function') _originalShowPage('login');
        else showPage('login');

    } catch (error) {
        showFormError('reset-update-error', error.message || 'Failed to update password.');
    } finally {
        setButtonLoading('reset-update-submit', false);
    }
}

// ============================================
// LOGOUT
// ============================================

async function handleLogout() {
    await sb.auth.signOut();
    window.location.href = '/';
}

// ============================================
// GOOGLE SIGN-IN
// ============================================

async function handleGoogleSignIn() {
    try {
        var result = await sb.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin + '/auth-callback',
                queryParams: {
                    prompt: 'select_account'
                }
            }
        });

        if (result.error) throw result.error;
        // Browser will redirect to Google — no further action needed here

    } catch (error) {
        console.error('Google sign-in error:', error);
        showToast('Google sign-in failed. Please try again.', 'error');
    }
}

/**
 * Ensures a users row + subscriptions row exist for OAuth sign-ins.
 * Called after Google sign-in callback when user may not have a profile yet.
 */
async function ensureProfileExists(user) {
    try {
        var existing = await sb.from('users').select('id').eq('id', user.id).single();
        if (existing.data) return; // Already exists

        var meta = user.user_metadata || {};
        var fullName = meta.full_name || meta.name || '';
        var firstName = meta.first_name || fullName.split(' ')[0] || '';
        var lastName = meta.last_name || fullName.split(' ').slice(1).join(' ') || '';
        var email = user.email || '';

        console.log('[Auth] Creating profile for OAuth user:', email);

        await sb.from('users').insert({
            id: user.id,
            email: email,
            first_name: firstName,
            last_name: lastName,
            primary_trade: 'other',
            experience_level: '1_3_years',
            account_type: 'free'
        });

        await sb.from('subscriptions').insert({
            user_id: user.id,
            plan: 'free',
            status: 'active'
        });
    } catch (err) {
        console.error('ensureProfileExists error:', err);
    }
}

// ============================================
// DASHBOARD NAVIGATION
// ============================================

async function navigateToDashboard() {
    try {
        // Use getSession (local, fast) instead of getUser (API call, can fail)
        var sessionResult = await sb.auth.getSession();
        var session = sessionResult.data.session;

        if (!session || !session.user) {
            if (typeof _originalShowPage === 'function') {
                _originalShowPage('login');
            } else {
                showPage('login');
            }
            return;
        }

        var user = session.user;

        // Check user plan — free users always go to individual
        var profileResult = await sb.from('users').select('account_type').eq('id', user.id).single();
        var accountType = profileResult.data ? profileResult.data.account_type : 'free';

        if (accountType === 'free') {
            localStorage.setItem('arrival_dashboard', 'individual');
            window.location.href = '/dashboard-individual';
        } else {
            var tmResult = await sb
                .from('team_members')
                .select('team_id')
                .eq('user_id', user.id)
                .eq('status', 'active')
                .limit(1);

            if (tmResult.data && tmResult.data.length > 0) {
                localStorage.setItem('arrival_dashboard', 'business');
                window.location.href = '/dashboard-business';
            } else {
                localStorage.setItem('arrival_dashboard', 'individual');
                window.location.href = '/dashboard-individual';
            }
        }
    } catch (err) {
        console.error('Dashboard navigation error:', err);
        // Fallback — use last known dashboard type, default to individual
        var lastDash = localStorage.getItem('arrival_dashboard') || 'individual';
        window.location.href = '/dashboard-' + lastDash;
    }
}


// ============================================
// DEV BYPASS
// ============================================

async function devSkipAsPro() {
    var email = 'pro@test.com';
    var password = 'testpass123';

    setButtonLoading('dev-skip-pro', true);

    try {
        // Try to sign in first
        var result = await sb.auth.signInWithPassword({ email: email, password: password });

        if (result.error && result.error.message.includes('Invalid login credentials')) {
            // User doesn't exist — create them
            var signUpResult = await sb.auth.signUp({
                email: email,
                password: password,
                options: { data: { first_name: 'Pro', last_name: 'Tester' } }
            });
            if (signUpResult.error) throw signUpResult.error;

            result = signUpResult;

            // Insert user profile
            await sb.from('users').upsert({
                id: result.data.user.id,
                email: email,
                first_name: 'Pro',
                last_name: 'Tester',
                primary_trade: 'hvac',
                experience_level: '3_10_years',
                account_type: 'pro'
            });

            // Insert pro subscription
            await sb.from('subscriptions').upsert({
                user_id: result.data.user.id,
                plan: 'pro',
                status: 'active'
            });

            // Re-sign in for proper session
            var loginResult = await sb.auth.signInWithPassword({ email: email, password: password });
            if (loginResult.error) throw loginResult.error;
            result = loginResult;
        } else if (result.error) {
            throw result.error;
        }

        // Ensure account_type is pro
        await sb.from('users').update({ account_type: 'pro' }).eq('id', result.data.user.id);

        window.location.href = '/dashboard-individual';

    } catch (err) {
        console.error('Dev skip pro error:', err);
        showToast('Dev bypass failed: ' + err.message, 'error');
    } finally {
        setButtonLoading('dev-skip-pro', false);
    }
}

async function devSkipAsBusinessAdmin() {
    var email = 'admin@test.com';
    var password = 'testpass123';

    setButtonLoading('dev-skip-business', true);

    try {
        // Try to sign in first
        var result = await sb.auth.signInWithPassword({ email: email, password: password });

        if (result.error && result.error.message.includes('Invalid login credentials')) {
            // Create admin user
            var signUpResult = await sb.auth.signUp({
                email: email,
                password: password,
                options: { data: { first_name: 'Admin', last_name: 'Tester' } }
            });
            if (signUpResult.error) throw signUpResult.error;

            result = signUpResult;
            var userId = result.data.user.id;

            // Insert user profile
            await sb.from('users').upsert({
                id: userId,
                email: email,
                first_name: 'Admin',
                last_name: 'Tester',
                primary_trade: 'hvac',
                experience_level: '10_plus_years',
                account_type: 'business'
            });

            // Insert business subscription
            await sb.from('subscriptions').upsert({
                user_id: userId,
                plan: 'business',
                status: 'active'
            });

            // Re-sign in for proper session
            var loginResult = await sb.auth.signInWithPassword({ email: email, password: password });
            if (loginResult.error) throw loginResult.error;
            result = loginResult;
            userId = result.data.user.id;

            // Create team + owner via RPC (bypasses RLS bootstrap problem)
            var teamResult = await sb.rpc('create_team_with_owner', {
                team_name: 'Test HVAC Co',
                team_trade: 'hvac',
                owner_user_id: userId,
                owner_email: email
            });
            if (teamResult.error) throw teamResult.error;

            var teamId = teamResult.data;

            // Add dummy team members
            await sb.from('team_members').insert([
                { team_id: teamId, email: 'tech1@test.com', role: 'technician', status: 'active' },
                { team_id: teamId, email: 'tech2@test.com', role: 'technician', status: 'invited', invited_at: new Date().toISOString() },
                { team_id: teamId, email: 'manager@test.com', role: 'manager', status: 'active' }
            ]);

            // Add dummy documents
            await sb.from('documents').insert([
                { uploaded_by: userId, team_id: teamId, file_name: 'Carrier-50XC-Manual.pdf', file_type: 'application/pdf', file_size: 2048000, storage_path: 'test/carrier-manual.pdf', category: 'equipment_manuals' },
                { uploaded_by: userId, team_id: teamId, file_name: 'Site-Survey-Jan.pdf', file_type: 'application/pdf', file_size: 1024000, storage_path: 'test/survey.pdf', category: 'site_surveys' }
            ]);

        } else if (result.error) {
            throw result.error;
        }

        // Find team
        var tmResult = await sb
            .from('team_members')
            .select('team_id')
            .eq('user_id', result.data.user.id)
            .eq('status', 'active')
            .limit(1);

        var teamId = tmResult.data && tmResult.data[0] ? tmResult.data[0].team_id : null;

        window.location.href = '/dashboard-business';

    } catch (err) {
        console.error('Dev skip business error:', err);
        showToast('Dev bypass failed: ' + err.message, 'error');
    } finally {
        setButtonLoading('dev-skip-business', false);
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', async function() {
    // Check if Supabase loaded
    if (typeof supabase === 'undefined') {
        showToast('Failed to load authentication. Please refresh.', 'error');
        return;
    }

    // Attach form handlers
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('signup-form').addEventListener('submit', handleSignup);
    document.getElementById('reset-request-form').addEventListener('submit', handlePasswordResetRequest);
    document.getElementById('reset-update-form').addEventListener('submit', handlePasswordUpdate);

    // Google sign-in buttons
    var googleBtns = document.querySelectorAll('.google-signin-btn');
    googleBtns.forEach(function(btn) {
        btn.addEventListener('click', handleGoogleSignIn);
    });

    // Dev bypass buttons
    if (IS_DEV) {
        var devBtns = document.getElementById('dev-bypass-buttons');
        devBtns.style.display = 'flex';
        document.getElementById('dev-skip-pro').addEventListener('click', devSkipAsPro);
        document.getElementById('dev-skip-business').addEventListener('click', devSkipAsBusinessAdmin);
    }

    // Check for password reset callback in URL hash
    var hash = window.location.hash;
    if (hash.includes('type=recovery') || hash.includes('access_token')) {
        var _showReset = typeof _originalShowPage === 'function' ? _originalShowPage : showPage;
        _showReset('reset-password');
        document.getElementById('reset-request-form').style.display = 'none';
        document.getElementById('reset-update-form').style.display = 'flex';
    }

    // Auth state listener
    sb.auth.onAuthStateChange(async function(event, session) {
        if (event === 'SIGNED_IN' && session) {
            updateNavForAuth(session.user);
            // Ensure profile exists for OAuth users
            await ensureProfileExists(session.user);
        } else if (event === 'SIGNED_OUT') {
            updateNavForAuth(null);
        } else if (event === 'PASSWORD_RECOVERY') {
            var _showReset2 = typeof _originalShowPage === 'function' ? _originalShowPage : showPage;
            _showReset2('reset-password');
            document.getElementById('reset-request-form').style.display = 'none';
            document.getElementById('reset-update-form').style.display = 'flex';
        }
    });

    // Check existing session on page load
    var sessionResult = await sb.auth.getSession();
    if (sessionResult.data.session) {
        updateNavForAuth(sessionResult.data.session.user);
    }
});

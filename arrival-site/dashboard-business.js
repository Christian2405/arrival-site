// ============================================
// ARRIVAL BUSINESS DASHBOARD - dashboard-business.js
// Supabase backend wiring for business dashboard
// ============================================

const SUPABASE_URL = 'https://nmmmrujtfrxrmajuggki.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tbW1ydWp0ZnJ4cm1hanVnZ2tpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1Mjk4NzEsImV4cCI6MjA4NzEwNTg3MX0.XaOQaqN_vbYSBeYFol63OzQFuKQYJ_pLXhMX7bvLAJQ';
const BACKEND_URL = 'https://arrival-backend-81x7.onrender.com/api';

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// State
let currentUser = null;
let currentProfile = null;
let currentSubscription = null;
let currentTeam = null;
let currentTeamMembership = null;
let teamMembers = [];
let teamDocs = [];

// Category display labels
const CATEGORY_LABELS = {
    manufacturer_manuals: 'Manufacturer Manuals',
    equipment_spec_sheets: 'Equipment Spec Sheets',
    company_sops: 'Company SOPs',
    safety_protocols: 'Safety Protocols',
    diagnostic_workflows: 'Diagnostic Workflows',
    training_materials: 'Training Materials',
    building_plans: 'Building Plans',
    parts_lists: 'Parts Lists',
    // Legacy categories (backward compat)
    equipment_manuals: 'Manufacturer Manuals',
    spec_sheets: 'Equipment Spec Sheets',
    sops: 'Company SOPs',
    wiring_diagrams: 'Manufacturer Manuals',
    technical_bulletins: 'Manufacturer Manuals',
    warranty_docs: 'Manufacturer Manuals'
};

// Map category DB values to filter tab categories
var CATEGORY_FILTERS = {
    manufacturer_manuals: 'manuals', equipment_manuals: 'manuals', wiring_diagrams: 'manuals',
    technical_bulletins: 'manuals', warranty_docs: 'manuals',
    equipment_spec_sheets: 'specs', spec_sheets: 'specs',
    company_sops: 'sops', sops: 'sops', installation_checklists: 'sops', maintenance_guides: 'sops',
    safety_protocols: 'safety', safety_data_sheets: 'safety', osha_docs: 'safety',
    diagnostic_workflows: 'diagnostics', inspection_checklists: 'diagnostics',
    training_materials: 'training',
    building_plans: 'plans', engineering_reports: 'plans', site_surveys: 'plans',
    permits: 'plans', project_specs: 'plans', scope_of_work: 'plans', material_specs: 'plans',
    parts_lists: 'parts'
};

// Member being targeted for removal (store ID)
var removeMemberId = null;

// ============================================
// TOAST
// ============================================

function showToast(message, type) {
    type = type || 'success';
    var container = document.getElementById('toast-container');
    var toast = document.createElement('div');
    toast.style.cssText = 'padding:12px 20px;border-radius:8px;color:#fff;font-size:14px;font-family:var(--font-body,DM Sans,sans-serif);box-shadow:0 4px 12px rgba(0,0,0,.15);animation:toast-in .3s ease;max-width:360px;';
    toast.style.background = type === 'error' ? '#c0392b' : '#27ae60';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 4000);
}

// ============================================
// AUTH GUARD & INIT
// ============================================

async function initAuth() {
    var result = await sb.auth.getSession();
    if (!result.data.session) {
        window.location.href = '/';
        return;
    }
    currentUser = result.data.session.user;

    // Load profile
    var profileResult = await sb.from('users').select('*').eq('id', currentUser.id).single();
    if (profileResult.data) currentProfile = profileResult.data;

    // Load subscription
    var subResult = await sb.from('subscriptions').select('*').eq('user_id', currentUser.id).eq('status', 'active').limit(1).single();
    if (subResult.data) currentSubscription = subResult.data;

    // Find team membership (retry if coming from checkout — webhook may still be processing)
    var isCheckoutReturn = window.location.search.includes('checkout=success');
    var memberResult = null;
    var maxAttempts = isCheckoutReturn ? 10 : 1;

    for (var attempt = 0; attempt < maxAttempts; attempt++) {
        memberResult = await sb.from('team_members')
            .select('*, teams(*)')
            .eq('user_id', currentUser.id)
            .eq('status', 'active')
            .limit(1)
            .single();

        if (memberResult.data) break;

        if (attempt < maxAttempts - 1) {
            // Wait 2 seconds before retrying (webhook may still be processing)
            await new Promise(function(resolve) { setTimeout(resolve, 2000); });
        }
    }

    if (!memberResult || !memberResult.data) {
        // Not a business team member — redirect to individual dashboard
        // Add stay=true to prevent redirect loop
        window.location.href = '/dashboard-individual?stay=true';
        return;
    }

    currentTeamMembership = memberResult.data;
    currentTeam = memberResult.data.teams;

    // Load all sections
    await Promise.all([
        loadHome(),
        loadDocuments(),
        loadMedia(),
        loadTeam(),
        loadPerTechActivity(),
        loadAnalytics(),
        loadBilling(),
        loadSettings()
    ]);

    // Show checkout success toast and clean URL
    if (isCheckoutReturn) {
        showToast('Subscription activated! Welcome to Business.');
        window.history.replaceState({}, '', window.location.pathname);
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
// DASHBOARD HOME
// ============================================

async function loadHome() {
    // Welcome message
    var firstName = currentProfile ? currentProfile.first_name : '';
    var el = document.getElementById('home-welcome');
    if (el) el.textContent = 'Welcome back, ' + (firstName || 'there') + '.';

    // Team members count (active)
    var membersResult = await sb.from('team_members')
        .select('id', { count: 'exact', head: true })
        .eq('team_id', currentTeam.id)
        .eq('status', 'active');
    var memberCount = membersResult.count || 0;
    document.getElementById('home-stat-members').textContent = memberCount;

    // Documents count
    var docsResult = await sb.from('documents')
        .select('id', { count: 'exact', head: true })
        .eq('team_id', currentTeam.id);
    var docCount = docsResult.count || 0;
    document.getElementById('home-stat-docs').innerHTML = docCount + ' <span class="stat-cap">uploaded</span>';

    // Queries — hardcoded to 0
    document.getElementById('home-stat-queries').textContent = '0';

    // Recent activity feed — combine recent documents + recent team member joins
    await loadActivityFeed();
}

async function loadActivityFeed() {
    var feed = document.getElementById('home-activity-feed');

    // Get recent documents (last 10)
    var docsResult = await sb.from('documents')
        .select('*, users!documents_uploaded_by_fkey(first_name, last_name)')
        .eq('team_id', currentTeam.id)
        .order('created_at', { ascending: false })
        .limit(10);

    // Get recent team member joins (last 5)
    var joinsResult = await sb.from('team_members')
        .select('*, users(first_name, last_name)')
        .eq('team_id', currentTeam.id)
        .not('joined_at', 'is', null)
        .order('joined_at', { ascending: false })
        .limit(5);

    var items = [];

    // Add document uploads
    if (docsResult.data) {
        docsResult.data.forEach(function(doc) {
            var name = doc.users ? (doc.users.first_name || '') + ' ' + (doc.users.last_name || '') : 'Unknown';
            items.push({
                time: new Date(doc.created_at),
                html: '<span class="activity-name">' + escapeHtml(name.trim()) + '</span> uploaded <em>' + escapeHtml(doc.file_name) + '</em>'
            });
        });
    }

    // Add team member joins
    if (joinsResult.data) {
        joinsResult.data.forEach(function(m) {
            var name = m.users ? (m.users.first_name || '') + ' ' + (m.users.last_name || '') : m.email;
            items.push({
                time: new Date(m.joined_at),
                html: '<span class="activity-name">' + escapeHtml(name.trim()) + '</span> joined the team'
            });
        });
    }

    // Sort by time descending, take first 10
    items.sort(function(a, b) { return b.time - a.time; });
    items = items.slice(0, 10);

    if (items.length === 0) {
        feed.innerHTML = '<div class="activity-item" style="color:var(--text-muted,#7c736a);">No recent activity yet.</div>';
        return;
    }

    feed.innerHTML = items.map(function(item) {
        return '<div class="activity-item">' + item.html + ' <span class="activity-time">' + timeAgo(item.time) + '</span></div>';
    }).join('');
}

// ============================================
// TEAM ANALYTICS
// ============================================

async function loadAnalytics() {
    // Stub — analytics data will be populated when query tracking is implemented
    // For now, display zero-state in all analytics tables
    var totalEl = document.getElementById('analytics-total-queries');
    var topicsEl = document.getElementById('analytics-unique-topics');
    var unansweredEl = document.getElementById('analytics-unanswered');
    var avgEl = document.getElementById('analytics-avg-per-tech');

    if (totalEl) totalEl.textContent = '0';
    if (topicsEl) topicsEl.textContent = '0';
    if (unansweredEl) unansweredEl.textContent = '0';
    if (avgEl) avgEl.textContent = '0';
}

// ============================================
// DOCUMENT LIBRARY
// ============================================

async function loadDocuments() {
    var result = await sb.from('documents')
        .select('*, users!documents_uploaded_by_fkey(first_name, last_name)')
        .eq('team_id', currentTeam.id)
        .order('created_at', { ascending: false });

    teamDocs = result.data || [];
    renderDocTable(teamDocs);

    // Update count
    var indicator = document.getElementById('doc-storage-indicator');
    if (indicator) indicator.textContent = teamDocs.length + ' documents uploaded. Unlimited on Business plan.';
}

function renderDocTable(docs) {
    var tbody = document.getElementById('doc-tbody');
    if (!tbody) return;

    if (docs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted,#7c736a);padding:32px;">No documents uploaded yet.</td></tr>';
        return;
    }

    tbody.innerHTML = docs.map(function(d) {
        var catLabel = CATEGORY_LABELS[d.category] || d.category;
        var catFilter = CATEGORY_FILTERS[d.category] || 'all';
        var uploaderName = d.users ? (d.users.first_name || '').charAt(0).toUpperCase() + (d.users.first_name || '').slice(1) + ' ' + ((d.users.last_name || '').charAt(0) || '') + '.' : '—';
        var statusClass = d.status === 'ready' ? 'status-ready' : 'status-processing';
        var statusLabel = d.status === 'ready' ? 'Ready' : 'Processing...';
        var date = new Date(d.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        var project = d.project_tag || '—';
        var viewDisabled = d.status !== 'ready' ? ' disabled' : '';

        return '<tr data-cat="' + catFilter + '">' +
            '<td class="td-name">' + escapeHtml(d.file_name) + '</td>' +
            '<td><span class="cat-pill">' + escapeHtml(catLabel) + '</span></td>' +
            '<td>' + escapeHtml(project) + '</td>' +
            '<td>' + escapeHtml(uploaderName) + '</td>' +
            '<td><span class="' + statusClass + '">' + statusLabel + '</span></td>' +
            '<td>' + date + '</td>' +
            '<td><a href="#" class="table-action' + viewDisabled + '" onclick="viewDocument(\'' + d.id + '\',\'' + d.storage_path + '\'); return false;">View</a> ' +
            '<a href="#" class="table-action table-action-danger" onclick="deleteDocument(\'' + d.id + '\',\'' + d.storage_path + '\'); return false;">Delete</a></td>' +
            '</tr>';
    }).join('');
}

function searchDocs(query) {
    var q = query.toLowerCase();
    if (!q) {
        renderDocTable(teamDocs);
        // Re-apply current filter tab
        var activeTab = document.querySelector('.filter-tabs .filter-tab.active');
        if (activeTab) {
            var cat = activeTab.getAttribute('onclick').match(/'([^']+)'/);
            if (cat && cat[1] !== 'all') {
                document.querySelectorAll('#doc-table tbody tr').forEach(function(row) {
                    if (row.dataset.cat !== cat[1]) row.style.display = 'none';
                });
            }
        }
        return;
    }
    var filtered = teamDocs.filter(function(d) {
        return d.file_name.toLowerCase().includes(q) ||
            (d.project_tag && d.project_tag.toLowerCase().includes(q)) ||
            (d.notes && d.notes.toLowerCase().includes(q)) ||
            (CATEGORY_LABELS[d.category] || '').toLowerCase().includes(q);
    });
    renderDocTable(filtered);
}

async function handleDocUpload() {
    var fileInput = document.getElementById('upload-file-input');
    var categorySelect = document.getElementById('upload-category');
    var projectInput = document.getElementById('upload-project');
    var notesInput = document.getElementById('upload-notes');

    if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Please select a file.', 'error');
        return;
    }

    var category = categorySelect.value;
    if (!category) {
        showToast('Please select a category.', 'error');
        return;
    }

    var file = fileInput.files[0];
    if (file.size > 100 * 1024 * 1024) {
        showToast('File exceeds 100MB limit.', 'error');
        return;
    }

    try {
        // Upload through backend API so RAG indexing happens automatically
        var session = (await sb.auth.getSession()).data.session;
        var token = session ? session.access_token : null;

        var formData = new FormData();
        formData.append('file', file);

        var resp = await fetch(BACKEND_URL + '/upload', {
            method: 'POST',
            headers: token ? { 'Authorization': 'Bearer ' + token } : {},
            body: formData,
        });

        if (!resp.ok) {
            var errBody = await resp.text();
            throw new Error(errBody || 'Upload failed');
        }

        showToast(file.name + ' uploaded & indexed.');
        closeModal('upload-modal');

        // Reset modal fields
        fileInput.value = '';
        categorySelect.value = '';
        projectInput.value = '';
        notesInput.value = '';

        // Reload documents and home stats
        await loadDocuments();
        loadHome();
    } catch (err) {
        console.error('Upload error:', err);
        showToast('Failed to upload: ' + err.message, 'error');
    }
}

async function viewDocument(docId, storagePath) {
    try {
        var signedResult = await sb.storage.from('documents').createSignedUrl(storagePath, 3600);
        if (signedResult.error) throw signedResult.error;
        window.open(signedResult.data.signedUrl, '_blank');
    } catch (err) {
        console.error('View error:', err);
        showToast('Failed to open document.', 'error');
    }
}

async function deleteDocument(docId, storagePath) {
    if (!confirm('Delete this document? This cannot be undone.')) return;

    try {
        // Delete through backend API so RAG vectors get cleaned up too
        var session = (await sb.auth.getSession()).data.session;
        var token = session ? session.access_token : null;

        var resp = await fetch(BACKEND_URL + '/documents/' + encodeURIComponent(docId), {
            method: 'DELETE',
            headers: token ? { 'Authorization': 'Bearer ' + token } : {},
        });

        if (!resp.ok) {
            var errBody = await resp.text();
            throw new Error(errBody || 'Delete failed');
        }

        showToast('Document deleted.');
        await loadDocuments();
        loadHome();
    } catch (err) {
        console.error('Delete error:', err);
        showToast('Failed to delete document.', 'error');
    }
}

// ============================================
// TEAM MANAGEMENT
// ============================================

async function loadTeam() {
    var result = await sb.from('team_members')
        .select('*, users(first_name, last_name)')
        .eq('team_id', currentTeam.id)
        .in('status', ['active', 'invited'])
        .order('status', { ascending: true })
        .order('joined_at', { ascending: true });

    teamMembers = result.data || [];
    renderTeamTable(teamMembers);
    updateSeatIndicator();
}

function renderTeamTable(members) {
    var tbody = document.getElementById('team-tbody');
    if (!tbody) return;

    if (members.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted,#7c736a);padding:32px;">No team members yet.</td></tr>';
        return;
    }

    var isAdmin = currentTeamMembership.role === 'admin';

    tbody.innerHTML = members.map(function(m) {
        var name, nameStyle = '';
        if (m.status === 'invited') {
            name = 'Pending';
            nameStyle = ' style="color:var(--text-muted)"';
        } else if (m.users) {
            name = (m.users.first_name || '') + ' ' + (m.users.last_name || '');
            name = name.trim() || m.email;
        } else {
            name = m.email;
        }

        var roleCap = m.role.charAt(0).toUpperCase() + m.role.slice(1);
        var statusClass = m.status === 'active' ? 'status-ready' : 'status-invited';
        var statusLabel = m.status === 'active' ? 'Active' : 'Invited';
        var joined = m.joined_at ? new Date(m.joined_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';

        var actions = '';
        if (isAdmin && m.user_id !== currentUser.id) {
            if (m.status === 'active') {
                actions = '<a href="#" class="table-action" onclick="promptChangeRole(\'' + m.id + '\',\'' + m.role + '\'); return false;">Change Role</a> ' +
                    '<a href="#" class="table-action table-action-danger" onclick="promptRemoveMember(\'' + m.id + '\'); return false;">Remove</a>';
            } else {
                actions = '<a href="#" class="table-action" onclick="resendInvite(\'' + m.id + '\',\'' + escapeHtml(m.email) + '\'); return false;">Resend</a> ' +
                    '<a href="#" class="table-action table-action-danger" onclick="promptRemoveMember(\'' + m.id + '\'); return false;">Remove</a>';
            }
        } else if (m.user_id === currentUser.id) {
            actions = '<span style="color:var(--text-muted,#7c736a);font-size:13px;">You</span>';
        }

        return '<tr>' +
            '<td class="td-name"' + nameStyle + '>' + escapeHtml(name) + '</td>' +
            '<td>' + escapeHtml(m.email) + '</td>' +
            '<td>' + roleCap + '</td>' +
            '<td><span class="' + statusClass + '">' + statusLabel + '</span></td>' +
            '<td>' + joined + '</td>' +
            '<td>' + actions + '</td>' +
            '</tr>';
    }).join('');
}

function updateSeatIndicator() {
    var usedSeats = teamMembers.filter(function(m) { return m.status === 'active' || m.status === 'invited'; }).length;
    var maxSeats = currentTeam.max_seats || 10;
    var el = document.getElementById('team-seat-indicator');
    if (el) {
        el.innerHTML = usedSeats + ' / ' + maxSeats + ' seats used. Additional seats: $250/month each. <button class="btn btn-sm btn-outline" style="margin-left:16px;" onclick="handleAddSeats()">Add Seats</button>';
    }
}

async function handleInvite() {
    var emailInput = document.getElementById('invite-email');
    var roleSelect = document.getElementById('invite-role');
    var email = emailInput.value.trim().toLowerCase();
    var role = roleSelect.value;

    if (!email) {
        showToast('Please enter an email address.', 'error');
        return;
    }

    // Check seat limit
    var usedSeats = teamMembers.filter(function(m) { return m.status === 'active' || m.status === 'invited'; }).length;
    if (usedSeats >= (currentTeam.max_seats || 10)) {
        showToast('Seat limit reached. Add more seats to invite members.', 'error');
        return;
    }

    try {
        var result = await sb.from('team_members').insert({
            team_id: currentTeam.id,
            email: email,
            role: role,
            status: 'invited',
            invited_at: new Date().toISOString()
        });

        if (result.error) {
            if (result.error.code === '23505') {
                showToast('This email is already on the team.', 'error');
            } else {
                throw result.error;
            }
            return;
        }

        showToast('Invite sent to ' + email + '.');
        closeModal('invite-modal');
        emailInput.value = '';
        roleSelect.value = 'technician';

        await loadTeam();
        loadHome();
    } catch (err) {
        console.error('Invite error:', err);
        showToast('Failed to send invite: ' + err.message, 'error');
    }
}

function promptChangeRole(memberId, currentRole) {
    var roles = ['admin', 'manager', 'technician'];
    var otherRoles = roles.filter(function(r) { return r !== currentRole; });
    var newRole = prompt('Change role to: ' + otherRoles.join(' or ') + '?', otherRoles[0]);
    if (!newRole) return;
    newRole = newRole.toLowerCase().trim();
    if (roles.indexOf(newRole) === -1) {
        showToast('Invalid role. Choose: admin, manager, or technician.', 'error');
        return;
    }
    changeRole(memberId, newRole);
}

async function changeRole(memberId, newRole) {
    try {
        var result = await sb.from('team_members').update({ role: newRole }).eq('id', memberId);
        if (result.error) throw result.error;
        showToast('Role updated to ' + newRole + '.');
        await loadTeam();
    } catch (err) {
        console.error('Change role error:', err);
        showToast('Failed to change role: ' + err.message, 'error');
    }
}

function promptRemoveMember(memberId) {
    removeMemberId = memberId;
    openModal('remove-modal');
}

async function handleRemoveMember() {
    if (!removeMemberId) return;

    try {
        var result = await sb.from('team_members').update({ status: 'deactivated' }).eq('id', removeMemberId);
        if (result.error) throw result.error;
        showToast('Team member removed.');
        closeModal('remove-modal');
        removeMemberId = null;
        await loadTeam();
        loadHome();
    } catch (err) {
        console.error('Remove member error:', err);
        showToast('Failed to remove member: ' + err.message, 'error');
    }
}

async function resendInvite(memberId, email) {
    showToast('Invite resent to ' + email + '.');
}

// ============================================
// PER-TECH ACTIVITY
// ============================================

async function loadPerTechActivity() {
    var tbody = document.getElementById('pertech-tbody');
    if (!tbody) return;

    // Get active team members (not current user if they are admin and want to see techs)
    var activeMembers = teamMembers.length > 0 ? teamMembers : [];
    if (activeMembers.length === 0) {
        // Re-fetch if not loaded yet
        var result = await sb.from('team_members')
            .select('*, users(first_name, last_name)')
            .eq('team_id', currentTeam.id)
            .eq('status', 'active');
        activeMembers = result.data || [];
    }

    if (activeMembers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted,#7c736a);padding:32px;">No team members yet. Invite your team to get started.</td></tr>';
        return;
    }

    tbody.innerHTML = activeMembers.filter(function(m) { return m.status === 'active'; }).map(function(m) {
        var name = m.users ? ((m.users.first_name || '') + ' ' + (m.users.last_name || '')).trim() : m.email;
        return '<tr>' +
            '<td class="td-name"><a href="#" class="drill-link" onclick="openDrillPanelForTech(\'' + m.id + '\',\'' + escapeHtml(name) + '\'); return false;">' + escapeHtml(name) + '</a></td>' +
            '<td>0</td>' +
            '<td>—</td>' +
            '<td>0</td>' +
            '</tr>';
    }).join('');
}

function openDrillPanelForTech(memberId, name) {
    var panel = document.getElementById('drill-panel');
    var overlay = document.getElementById('drill-overlay');
    var title = document.getElementById('drill-title');
    var sub = document.getElementById('drill-sub');
    var searchInput = document.getElementById('drill-search-input');
    var list = document.getElementById('drill-list');

    searchInput.value = '';
    title.textContent = name;
    sub.textContent = '0 queries this period';
    list.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-light);">No queries yet. Queries will appear here once ' + escapeHtml(name) + ' uses Arrival in the field.</div>';

    // Clear the hardcoded drillData items
    if (typeof currentDrillItems !== 'undefined') currentDrillItems = [];

    panel.classList.add('open');
    overlay.classList.add('open');
}

// ============================================
// PHOTOS & VIDEOS
// ============================================

var teamMedia = [];

async function loadMedia() {
    // Query documents table for media files (category = 'photo' or 'video')
    var result = await sb.from('documents')
        .select('*, users!documents_uploaded_by_fkey(first_name, last_name)')
        .eq('team_id', currentTeam.id)
        .in('category', ['photo', 'video'])
        .order('created_at', { ascending: false });

    teamMedia = result.data || [];
    renderMediaGrid(teamMedia);

    var indicator = document.getElementById('media-storage-indicator');
    if (indicator) indicator.textContent = teamMedia.length + ' files uploaded · Unlimited on Business plan.';
}

function renderMediaGrid(items) {
    var grid = document.getElementById('media-grid');
    if (!grid) return;

    if (items.length === 0) {
        grid.innerHTML = '<div style="padding:48px 20px;text-align:center;color:var(--text-muted,#7c736a);width:100%;">No photos or videos uploaded yet.</div>';
        return;
    }

    var photoSvg = '<svg width="32" height="32" fill="none" stroke="#9a9590" stroke-width="1.5"><rect x="4" y="6" width="24" height="20" rx="3"/><circle cx="12" cy="14" r="3"/><path d="M28 22l-6-7-5 6-3-3-6 6"/></svg>';
    var videoSvg = '<svg width="32" height="32" fill="none" stroke="#9a9590" stroke-width="1.5"><polygon points="12,8 26,16 12,24"/></svg>';

    grid.innerHTML = items.map(function(m) {
        var isVideo = m.category === 'video' || (m.file_type && m.file_type.startsWith('video/'));
        var mediaType = isVideo ? 'video' : 'photo';
        var thumbClass = isVideo ? 'media-thumb media-thumb-video' : 'media-thumb';
        var svg = isVideo ? videoSvg : photoSvg;
        var ext = m.file_name.split('.').pop().toUpperCase();
        var sizeMB = (m.file_size / (1024 * 1024)).toFixed(1);
        var date = new Date(m.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        var uploaderName = m.users ? (m.users.first_name || '').charAt(0).toUpperCase() + (m.users.first_name || '').slice(1) + ' ' + ((m.users.last_name || '').charAt(0) || '') + '.' : '';
        var title = m.notes || m.file_name;
        var site = m.project_tag ? '<div class="media-meta">Site: ' + escapeHtml(m.project_tag) + '</div>' : '';

        return '<div class="media-card" data-media="' + mediaType + '">' +
            '<div class="' + thumbClass + '" style="background:#e8e4df;">' + svg + '</div>' +
            '<div class="media-info">' +
                '<div class="media-name">' + escapeHtml(title) + '</div>' +
                '<div class="media-meta">' + ext + ' · ' + sizeMB + ' MB · ' + date + (uploaderName ? ' · Uploaded by ' + escapeHtml(uploaderName) : '') + '</div>' +
                site +
            '</div>' +
            '<div class="media-actions"><a href="#" class="table-action" onclick="viewMedia(\'' + m.id + '\',\'' + m.storage_path + '\'); return false;">View</a> <a href="#" class="table-action table-action-danger" onclick="deleteMedia(\'' + m.id + '\',\'' + m.storage_path + '\'); return false;">Delete</a></div>' +
            '</div>';
    }).join('');
}

function searchMedia(query) {
    var q = query.toLowerCase();
    if (!q) {
        renderMediaGrid(teamMedia);
        return;
    }
    var filtered = teamMedia.filter(function(m) {
        return m.file_name.toLowerCase().includes(q) ||
            (m.notes && m.notes.toLowerCase().includes(q)) ||
            (m.project_tag && m.project_tag.toLowerCase().includes(q));
    });
    renderMediaGrid(filtered);
}

async function handleMediaUpload() {
    var fileInput = document.getElementById('media-file-input');
    var titleInput = document.getElementById('media-title');
    var projectInput = document.getElementById('media-project');
    var notesInput = document.getElementById('media-notes');

    if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Please select a file.', 'error');
        return;
    }

    var file = fileInput.files[0];
    if (file.size > 200 * 1024 * 1024) {
        showToast('File exceeds 200MB limit.', 'error');
        return;
    }

    var isVideo = file.type.startsWith('video/');
    var category = isVideo ? 'video' : 'photo';
    var storagePath = 'teams/' + currentTeam.id + '/media/' + Date.now() + '_' + file.name;

    try {
        var uploadResult = await sb.storage.from('documents').upload(storagePath, file);
        if (uploadResult.error) throw uploadResult.error;

        var ext = file.name.split('.').pop().toLowerCase();
        var insertResult = await sb.from('documents').insert({
            uploaded_by: currentUser.id,
            team_id: currentTeam.id,
            file_name: file.name,
            file_type: file.type || (isVideo ? 'video/' + ext : 'image/' + ext),
            file_size: file.size,
            storage_path: storagePath,
            category: category,
            project_tag: projectInput.value.trim() || null,
            notes: titleInput.value.trim() || notesInput.value.trim() || null,
            status: 'ready'
        });
        if (insertResult.error) throw insertResult.error;

        showToast(file.name + ' uploaded successfully.');
        closeModal('media-upload-modal');

        fileInput.value = '';
        titleInput.value = '';
        projectInput.value = '';
        notesInput.value = '';

        await loadMedia();
    } catch (err) {
        console.error('Media upload error:', err);
        showToast('Failed to upload: ' + err.message, 'error');
    }
}

async function viewMedia(id, storagePath) {
    try {
        var signedResult = await sb.storage.from('documents').createSignedUrl(storagePath, 3600);
        if (signedResult.error) throw signedResult.error;
        window.open(signedResult.data.signedUrl, '_blank');
    } catch (err) {
        console.error('View media error:', err);
        showToast('Failed to open file.', 'error');
    }
}

async function deleteMedia(id, storagePath) {
    if (!confirm('Delete this file? This cannot be undone.')) return;

    try {
        await sb.storage.from('documents').remove([storagePath]);
        var dbResult = await sb.from('documents').delete().eq('id', id);
        if (dbResult.error) throw dbResult.error;
        showToast('File deleted.');
        await loadMedia();
    } catch (err) {
        console.error('Delete media error:', err);
        showToast('Failed to delete file.', 'error');
    }
}

// ============================================
// SUBSCRIPTION & BILLING
// ============================================

function loadBilling() {
    var seatCount = teamMembers.filter(function(m) { return m.status === 'active' || m.status === 'invited'; }).length;
    var maxSeats = currentTeam ? (currentTeam.max_seats || 10) : 10;
    var extraSeats = Math.max(0, maxSeats - 10);
    var extraCost = extraSeats * 250;
    var total = 250 + extraCost;

    document.getElementById('billing-plan-name').textContent = 'Business Plan';
    document.getElementById('billing-plan-price').textContent = '$250/month';
    document.getElementById('billing-seats-detail').textContent = '10 base seats' + (extraSeats > 0 ? ' + ' + extraSeats + ' extra ($' + extraCost + '/mo)' : '') + ', ' + seatCount + ' in use';
    document.getElementById('billing-total').textContent = 'Monthly total: $' + total.toFixed(2);

    // Show next billing date if available
    if (currentSubscription && currentSubscription.current_period_end) {
        var endDate = new Date(currentSubscription.current_period_end);
        var el = document.getElementById('billing-next-date');
        if (el) el.textContent = 'Next billing: ' + endDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    }
}

async function openBillingPortal() {
    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        showToast('Opening billing portal...');
        var response = await fetch('/.netlify/functions/create-portal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ userId: currentUser.id })
        });

        var data = await response.json();
        if (data.url) {
            window.location.href = data.url;
        } else {
            showToast(data.error || 'Failed to open billing portal.', 'error');
        }
    } catch (err) {
        console.error('Portal error:', err);
        showToast('Something went wrong.', 'error');
    }
}

async function handleAddSeats() {
    var countStr = prompt('How many extra seats to add? ($250/month each)', '1');
    var count = parseInt(countStr, 10);
    if (!count || count < 1) return;

    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        showToast('Adding seats...');
        var response = await fetch('/.netlify/functions/update-seats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ action: 'add', count: count })
        });

        var data = await response.json();
        if (data.success) {
            showToast(count + ' seat(s) added. Total: ' + data.newSeatCount + ' seats.');
            if (currentTeam) currentTeam.max_seats = data.newSeatCount;
            loadBilling();
            updateSeatIndicator();
        } else {
            showToast(data.error || 'Failed to add seats.', 'error');
        }
    } catch (err) {
        showToast('Failed to add seats.', 'error');
    }
}

async function handleRemoveSeats() {
    var countStr = prompt('How many seats to remove?', '1');
    var count = parseInt(countStr, 10);
    if (!count || count < 1) return;

    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        showToast('Removing seats...');
        var response = await fetch('/.netlify/functions/update-seats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ action: 'remove', count: count })
        });

        var data = await response.json();
        if (data.success) {
            showToast(count + ' seat(s) removed. Total: ' + data.newSeatCount + ' seats.');
            if (currentTeam) currentTeam.max_seats = data.newSeatCount;
            loadBilling();
            updateSeatIndicator();
        } else {
            showToast(data.error || 'Failed to remove seats.', 'error');
        }
    } catch (err) {
        showToast('Failed to remove seats.', 'error');
    }
}

// ============================================
// ACCOUNT SETTINGS
// ============================================

function loadSettings() {
    if (!currentProfile || !currentTeam) return;

    // Company Profile
    document.getElementById('settings-company-name').value = currentTeam.name || '';
    document.getElementById('settings-company-trade').value = currentTeam.primary_trade || 'hvac';
    document.getElementById('settings-company-employees').value = currentTeam.employee_count ? getEmployeeRange(currentTeam.employee_count) : '6-15';
    document.getElementById('settings-company-address').value = currentTeam.address || '';

    // Personal Profile
    document.getElementById('settings-first-name').value = currentProfile.first_name || '';
    document.getElementById('settings-last-name').value = currentProfile.last_name || '';
    document.getElementById('settings-email').value = currentProfile.email || currentUser.email || '';

    // Preferences
    var units = currentProfile.preferred_units || 'imperial';
    document.querySelectorAll('#pref-units .toggle-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.getAttribute('data-value') === units);
    });

    var depth = currentProfile.explanation_depth || 'standard';
    document.querySelectorAll('input[name="depth"]').forEach(function(radio) {
        radio.checked = radio.value === depth;
    });
}

function getEmployeeRange(count) {
    if (count <= 5) return '1-5';
    if (count <= 15) return '6-15';
    if (count <= 50) return '16-50';
    if (count <= 200) return '51-200';
    return '200+';
}

function getEmployeeCount(range) {
    var map = { '1-5': 5, '6-15': 10, '16-50': 30, '51-200': 100, '200+': 250 };
    return map[range] || 10;
}

async function handleSaveCompanyProfile() {
    var name = document.getElementById('settings-company-name').value.trim();
    var trade = document.getElementById('settings-company-trade').value;
    var employeeRange = document.getElementById('settings-company-employees').value;
    var address = document.getElementById('settings-company-address').value.trim();

    if (!name) {
        showToast('Company name is required.', 'error');
        return;
    }

    try {
        var result = await sb.from('teams').update({
            name: name,
            primary_trade: trade,
            employee_count: getEmployeeCount(employeeRange),
            address: address
        }).eq('id', currentTeam.id);

        if (result.error) throw result.error;

        currentTeam.name = name;
        currentTeam.primary_trade = trade;
        currentTeam.employee_count = getEmployeeCount(employeeRange);
        currentTeam.address = address;

        showToast('Company profile saved.');
    } catch (err) {
        console.error('Save company error:', err);
        showToast('Failed to save: ' + err.message, 'error');
    }
}

async function handleSavePersonalProfile() {
    var firstName = document.getElementById('settings-first-name').value.trim();
    var lastName = document.getElementById('settings-last-name').value.trim();

    // Preferences
    var unitsBtn = document.querySelector('#pref-units .toggle-btn.active');
    var units = unitsBtn ? unitsBtn.getAttribute('data-value') : 'imperial';

    var depthRadio = document.querySelector('input[name="depth"]:checked');
    var depth = depthRadio ? depthRadio.value : 'standard';

    try {
        var result = await sb.from('users').update({
            first_name: firstName,
            last_name: lastName,
            preferred_units: units,
            explanation_depth: depth
        }).eq('id', currentUser.id);

        if (result.error) throw result.error;

        currentProfile.first_name = firstName;
        currentProfile.last_name = lastName;
        currentProfile.preferred_units = units;
        currentProfile.explanation_depth = depth;

        showToast('Profile saved.');
    } catch (err) {
        console.error('Save profile error:', err);
        showToast('Failed to save: ' + err.message, 'error');
    }
}

async function handleUpdatePassword() {
    var newPw = document.getElementById('settings-new-password').value;
    var confirmPw = document.getElementById('settings-confirm-password').value;

    if (!newPw) {
        showToast('Please enter a new password.', 'error');
        return;
    }
    if (newPw.length < 6) {
        showToast('Password must be at least 6 characters.', 'error');
        return;
    }
    if (newPw !== confirmPw) {
        showToast('Passwords do not match.', 'error');
        return;
    }

    try {
        var result = await sb.auth.updateUser({ password: newPw });
        if (result.error) throw result.error;

        document.getElementById('settings-new-password').value = '';
        document.getElementById('settings-confirm-password').value = '';
        showToast('Password updated.');
    } catch (err) {
        console.error('Password update error:', err);
        showToast('Failed to update password: ' + err.message, 'error');
    }
}

// ============================================
// DELETE ACCOUNT
// ============================================

async function handleDeleteAccount() {
    var input = document.getElementById('delete-confirm-input');
    if (input.value.trim() !== 'DELETE') {
        showToast('Please type DELETE to confirm.', 'error');
        return;
    }

    try {
        // 1. Delete all team files from storage
        var listResult = await sb.storage.from('documents').list('teams/' + currentTeam.id);
        if (listResult.data && listResult.data.length > 0) {
            var paths = listResult.data.map(function(f) { return 'teams/' + currentTeam.id + '/' + f.name; });
            await sb.storage.from('documents').remove(paths);
        }

        // 2. Delete personal files
        var personalResult = await sb.storage.from('documents').list(currentUser.id);
        if (personalResult.data && personalResult.data.length > 0) {
            var personalPaths = personalResult.data.map(function(f) { return currentUser.id + '/' + f.name; });
            await sb.storage.from('documents').remove(personalPaths);
        }

        // 3. Delete auth user via RPC (cascades to all DB rows)
        var rpcResult = await sb.rpc('delete_own_account');
        if (rpcResult.error) throw rpcResult.error;

        // 4. Sign out and redirect
        await sb.auth.signOut();
        window.location.href = '/';
    } catch (err) {
        console.error('Delete account error:', err);
        showToast('Failed to delete account: ' + err.message, 'error');
    }
}

// ============================================
// HELPERS
// ============================================

function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function timeAgo(date) {
    var now = new Date();
    var diff = now - date;
    var mins = Math.floor(diff / 60000);
    var hours = Math.floor(diff / 3600000);
    var days = Math.floor(diff / 86400000);

    if (mins < 1) return 'Just now';
    if (mins < 60) return mins + ' min ago';
    if (hours < 24) return hours + ' hour' + (hours === 1 ? '' : 's') + ' ago';
    if (days < 7) {
        if (days === 1) return 'Yesterday';
        return days + ' days ago';
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Upload document button
    document.getElementById('upload-submit-btn').addEventListener('click', handleDocUpload);

    // Upload media button
    document.getElementById('media-upload-btn').addEventListener('click', handleMediaUpload);

    // Invite team member
    document.getElementById('invite-send-btn').addEventListener('click', handleInvite);

    // Remove team member confirm
    document.getElementById('remove-confirm-btn').addEventListener('click', handleRemoveMember);

    // Company profile save
    document.getElementById('settings-company-save-btn').addEventListener('click', handleSaveCompanyProfile);

    // Personal profile save
    document.getElementById('settings-profile-save-btn').addEventListener('click', handleSavePersonalProfile);

    // Password update
    document.getElementById('settings-password-btn').addEventListener('click', handleUpdatePassword);

    // Delete account
    document.getElementById('delete-confirm-btn').addEventListener('click', handleDeleteAccount);

    // Billing — Add/Remove seats
    document.getElementById('billing-add-seats-btn').addEventListener('click', handleAddSeats);
    document.getElementById('billing-remove-seats-btn').addEventListener('click', handleRemoveSeats);

    // Billing — Cancel subscription (opens portal)
    document.getElementById('billing-cancel-btn').addEventListener('click', function() {
        openModal('cancel-modal');
    });
    document.getElementById('cancel-confirm-btn').addEventListener('click', async function() {
        closeModal('cancel-modal');
        await openBillingPortal();
    });

    // Billing — Update payment (opens portal)
    document.getElementById('billing-update-payment-btn').addEventListener('click', async function() {
        await openBillingPortal();
    });

    // Billing — Invoice links (opens portal)
    document.querySelectorAll('#billing-invoice-section .table-action').forEach(function(link) {
        link.addEventListener('click', async function(e) {
            e.preventDefault();
            await openBillingPortal();
        });
    });

    // Auth check & load data
    initAuth();
});

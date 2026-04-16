// ============================================
// ARRIVAL BUSINESS DASHBOARD - dashboard-business.js
// Supabase backend wiring for business dashboard
// ============================================

const SUPABASE_URL = 'https://nmmmrujtfrxrmajuggki.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tbW1ydWp0ZnJ4cm1hanVnZ2tpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1Mjk4NzEsImV4cCI6MjA4NzEwNTg3MX0.XaOQaqN_vbYSBeYFol63OzQFuKQYJ_pLXhMX7bvLAJQ';
const BACKEND_URL = 'https://arrival-backend-81x7.onrender.com/api';

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: { lock: function(_name, _acquireTimeout, fn) { return fn(); } }
});

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
    var icon = type === 'error' ? '✕' : '✓';
    toast.style.cssText = 'padding:12px 20px;border-radius:8px;color:#fff;font-size:14px;font-family:var(--font-body,DM Sans,sans-serif);box-shadow:0 4px 16px rgba(0,0,0,.18);animation:toast-in .3s ease;max-width:360px;background:#2A2622;';
    toast.textContent = icon + '  ' + message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 4000);
}

// ============================================
// UPLOAD OVERLAY (dynamically created)
// ============================================

function ensureUploadOverlay() {
    if (document.getElementById('upload-overlay')) return;
    var overlay = document.createElement('div');
    overlay.className = 'upload-overlay';
    overlay.id = 'upload-overlay';
    overlay.innerHTML = '<div class="upload-spinner"></div><div class="upload-overlay-text" id="upload-overlay-text">Uploading...</div>';
    document.body.appendChild(overlay);
}

function showUploadOverlay(text) {
    ensureUploadOverlay();
    var overlay = document.getElementById('upload-overlay');
    var textEl = document.getElementById('upload-overlay-text');
    if (textEl) textEl.textContent = text || 'Uploading...';
    if (overlay) overlay.classList.add('active');
}

function hideUploadOverlay() {
    var overlay = document.getElementById('upload-overlay');
    if (overlay) overlay.classList.remove('active');
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
    var subResult = await sb.from('subscriptions').select('*').eq('user_id', currentUser.id).in('status', ['active', 'trial_expired']).limit(1).single();
    if (subResult.data) currentSubscription = subResult.data;

    // Check if trial has expired
    var subStatus = currentSubscription ? currentSubscription.status : 'active';
    if (subStatus === 'trial_expired') {
        showTrialExpiredOverlay();
        return;
    }
    if (currentSubscription && currentSubscription.trial_ends_at && !currentSubscription.stripe_subscription_id) {
        var trialEnd = new Date(currentSubscription.trial_ends_at);
        if (trialEnd < new Date()) {
            showTrialExpiredOverlay();
            return;
        }
    }

    // Pro plan users without a team always go to individual dashboard
    var subPlan = currentSubscription ? currentSubscription.plan : 'pro';
    if (subPlan === 'pro') {
        window.location.href = '/dashboard-individual';
        return;
    }

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
        loadTeam(),
        loadPerTechActivity(),
        loadBilling(),
        loadSettings()
    ]);

    // Show checkout success toast and clean URL
    if (isCheckoutReturn) {
        showToast('Subscription activated! Welcome to Business.');
        window.history.replaceState({}, '', window.location.pathname);
    }
}

function showTrialExpiredOverlay() {
    var overlay = document.getElementById('trial-expired-overlay');
    if (overlay) overlay.style.display = 'flex';
}

// ============================================
// LOGOUT
// ============================================

function handleLogout() {
    localStorage.removeItem('arrival_dashboard');
    sb.auth.signOut().catch(function () {});
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

    // Queries — count from queries table
    var queriesResult = await sb.from('queries')
        .select('id', { count: 'exact', head: true })
        .eq('team_id', currentTeam.id);
    var queryCount = queriesResult.count || 0;
    document.getElementById('home-stat-queries').textContent = queryCount;

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

    // Get recent queries (last 10)
    var queriesResult = await sb.from('queries')
        .select('*, users!queries_user_id_fkey(first_name, last_name)')
        .eq('team_id', currentTeam.id)
        .order('created_at', { ascending: false })
        .limit(10);

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

    // Add queries
    if (queriesResult.data) {
        queriesResult.data.forEach(function(q) {
            var name = q.users ? (q.users.first_name || '') + ' ' + (q.users.last_name || '') : 'Team member';
            var shortQ = q.question.length > 60 ? q.question.substring(0, 57) + '...' : q.question;
            items.push({
                time: new Date(q.created_at),
                html: '<span class="activity-name">' + escapeHtml(name.trim()) + '</span> asked <em>"' + escapeHtml(shortQ) + '"</em>'
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
// DOCUMENT LIBRARY
// ============================================

var docThumbUrls = {};

async function loadDocuments() {
    var result = await sb.from('documents')
        .select('*, users!documents_uploaded_by_fkey(first_name, last_name)')
        .eq('team_id', currentTeam.id)
        .not('category', 'in', '("photo","video")')
        .order('created_at', { ascending: false });

    teamDocs = result.data || [];

    // Get signed URLs for image-type documents (for thumbnails)
    var imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
    var imageDocs = teamDocs.filter(function(d) {
        var ext = d.file_name.split('.').pop().toLowerCase();
        return imageExts.indexOf(ext) !== -1;
    });
    docThumbUrls = {};
    if (imageDocs.length > 0) {
        var paths = imageDocs.map(function(d) { return d.storage_path; });
        var signedResults = await sb.storage.from('documents').createSignedUrls(paths, 3600);
        if (signedResults.data) {
            signedResults.data.forEach(function(r) {
                if (r.signedUrl) docThumbUrls[r.path] = r.signedUrl;
            });
        }
    }

    renderDocTable(teamDocs);

    // Auto-poll if any docs are still processing
    var hasProcessing = teamDocs.some(function(d) { return d.status !== 'indexed' && d.status !== 'ready' && d.status !== 'index_failed'; });
    if (hasProcessing && !window._docAutoRefresh) {
        window._docAutoRefresh = setInterval(function() {
            loadDocuments();
        }, 10000);
    } else if (!hasProcessing && window._docAutoRefresh) {
        clearInterval(window._docAutoRefresh);
        window._docAutoRefresh = null;
    }

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
        var ext = d.file_name.split('.').pop().toLowerCase();
        var extUpper = ext.toUpperCase();
        var catLabel = CATEGORY_LABELS[d.category] || d.category;
        var catFilter = CATEGORY_FILTERS[d.category] || 'all';
        var uploaderName = d.users ? (d.users.first_name || '').charAt(0).toUpperCase() + (d.users.first_name || '').slice(1) + ' ' + ((d.users.last_name || '').charAt(0) || '') + '.' : '—';
        var statusClass, statusLabel;
        if (d.status === 'indexed' || d.status === 'ready') {
            statusClass = 'status-ready'; statusLabel = 'Ready';
        } else if (d.status === 'index_failed') {
            statusClass = 'status-failed'; statusLabel = 'Index failed';
        } else {
            statusClass = 'status-processing'; statusLabel = 'Indexing… <span class="info-tip" title="Your document is being read and indexed so Arrival can reference it when answering questions. This usually takes 1–5 minutes depending on file size.">ⓘ</span>';
        }
        var date = new Date(d.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        var project = d.project_tag || '—';
        var viewDisabled = '';

        // Build thumbnail
        var thumb;
        if (docThumbUrls[d.storage_path]) {
            thumb = '<div class="doc-thumb"><img src="' + docThumbUrls[d.storage_path] + '" alt=""></div>';
        } else if (ext === 'pdf') {
            thumb = '<div class="doc-thumb doc-thumb-pdf"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#c45a3c" stroke-width="1.5" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span class="doc-thumb-label">PDF</span></div>';
        } else {
            thumb = '<div class="doc-thumb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9a9590" stroke-width="1.5" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span class="doc-thumb-label">' + extUpper + '</span></div>';
        }

        return '<tr data-cat="' + catFilter + '">' +
            '<td class="td-name"><div class="doc-name-cell">' + thumb + '<span>' + escapeHtml(d.file_name) + '</span></div></td>' +
            '<td><span class="cat-pill">' + escapeHtml(catLabel) + '</span></td>' +
            '<td>' + escapeHtml(project) + '</td>' +
            '<td>' + escapeHtml(uploaderName) + '</td>' +
            '<td><span class="' + statusClass + '">' + statusLabel + '</span></td>' +
            '<td>' + date + '</td>' +
            '<td><a href="#" class="table-action" onclick="viewDocument(\'' + d.id + '\',\'' + escapeAttr(d.storage_path) + '\'); return false;">View</a> ' +
            '<a href="#" class="table-action" onclick="openEditDocument(\'' + d.id + '\'); return false;">Edit</a> ' +
            (d.status === 'index_failed' ? '<a href="#" class="table-action" onclick="retryIndexDocument(\'' + escapeAttr(d.id) + '\',\'' + escapeAttr(d.storage_path) + '\'); return false;">Retry</a> ' : '') +
            '<a href="#" class="table-action table-action-danger" onclick="deleteDocument(\'' + d.id + '\',\'' + escapeAttr(d.storage_path) + '\'); return false;">Delete</a></td>' +
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

function _pollUntilIndexed(docId) {
    var deadline = Date.now() + 10 * 60 * 1000;
    function check() {
        if (Date.now() > deadline) return;
        sb.from('documents').select('status').eq('id', docId).single().then(function(result) {
            var status = result.data && result.data.status;
            if (status === 'ready' || status === 'indexed' || status === 'index_failed') {
                loadDocuments();
                loadHome();
                if (status === 'ready' || status === 'indexed') showToast('Document ready — AI can now use it.');
                if (status === 'index_failed') showToast('Indexing failed — click Retry in the doc list.', 'error');
            } else {
                setTimeout(check, 8000);
            }
        });
    }
    setTimeout(check, 8000);
}

async function retryIndexDocument(docId, storagePath) {
    var session = (await sb.auth.getSession()).data.session;
    if (!session) { showToast('Not logged in.', 'error'); return; }
    await sb.from('documents').update({ status: 'processing' }).eq('id', docId);
    await loadDocuments();
    showToast('Re-indexing…');
    try {
        var r = await fetch(BACKEND_URL + '/index-document', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + session.access_token, 'Content-Type': 'application/json' },
            body: JSON.stringify({ document_id: docId, storage_path: storagePath }),
        });
        if (r.ok) {
            _pollUntilIndexed(docId);
        } else {
            showToast('Failed to start indexing.', 'error');
        }
    } catch (_) {
        showToast('Failed to reach backend.', 'error');
    }
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

    closeModal('upload-modal');
    showUploadOverlay('Uploading ' + file.name + '...');

    try {
        var session = (await sb.auth.getSession()).data.session;
        if (!session) throw new Error('Not authenticated');

        var formData = new FormData();
        formData.append('file', file);
        formData.append('category', category);
        if (currentTeam) formData.append('team_id', currentTeam.id);
        if (projectInput.value.trim()) formData.append('project_tag', projectInput.value.trim());
        if (notesInput.value.trim()) formData.append('notes', notesInput.value.trim());

        var uploadResp = await fetch(BACKEND_URL + '/upload', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + session.access_token },
            body: formData,
        });
        if (!uploadResp.ok) {
            var errText = await uploadResp.text();
            throw new Error(errText || 'Upload failed');
        }
        var uploadData = await uploadResp.json();

        hideUploadOverlay();
        showToast(file.name + ' uploaded — indexing in background.');

        fileInput.value = '';
        categorySelect.value = '';
        projectInput.value = '';
        notesInput.value = '';

        await loadDocuments();
        loadHome();

        _pollUntilIndexed(uploadData.id);

    } catch (err) {
        console.error('Upload error:', err);
        hideUploadOverlay();
        showToast('Failed to upload ' + file.name + ': ' + (err.message || 'Unknown error'), 'error');
    }
}

async function viewDocument(docId, storagePath) {
    // Open window synchronously BEFORE the await — Safari blocks window.open() after async calls
    var win = window.open('', '_blank');
    try {
        var signedResult = await sb.storage.from('documents').createSignedUrl(storagePath, 3600);
        if (signedResult.error) throw signedResult.error;
        win.location.href = signedResult.data.signedUrl;
    } catch (err) {
        if (win) win.close();
        console.error('View error:', err);
        showToast('Failed to open document.', 'error');
    }
}

var pendingDeleteDocId = null;
var pendingDeleteStoragePath = null;

function deleteDocument(docId, storagePath) {
    pendingDeleteDocId = docId;
    pendingDeleteStoragePath = storagePath;
    openModal('delete-doc-modal');
}

async function confirmDeleteDocument() {
    var docId = pendingDeleteDocId;
    closeModal('delete-doc-modal');
    pendingDeleteDocId = null;
    pendingDeleteStoragePath = null;
    if (!docId) return;

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
        showToast('Failed to delete document. Please try again later.', 'error');
    }
}

function openEditDocument(docId) {
    var doc = teamDocs.find(function(d) { return d.id === docId; });
    if (!doc) { showToast('Document not found.', 'error'); return; }

    document.getElementById('edit-doc-id').value = doc.id;
    document.getElementById('edit-doc-storage-path').value = doc.storage_path;
    document.getElementById('edit-doc-name').value = doc.file_name;
    document.getElementById('edit-doc-category').value = doc.category;
    document.getElementById('edit-doc-project').value = doc.project_tag || '';
    document.getElementById('edit-doc-notes').value = doc.notes || '';
    document.getElementById('edit-doc-file').value = '';

    openModal('edit-doc-modal');
}

async function handleEditDocSave() {
    var docId = document.getElementById('edit-doc-id').value;
    var oldStoragePath = document.getElementById('edit-doc-storage-path').value;
    var newName = document.getElementById('edit-doc-name').value.trim();
    var newCategory = document.getElementById('edit-doc-category').value;
    var newProject = document.getElementById('edit-doc-project').value.trim() || null;
    var newNotes = document.getElementById('edit-doc-notes').value.trim() || null;
    var fileInput = document.getElementById('edit-doc-file');
    var replaceFile = fileInput.files && fileInput.files.length > 0;

    if (!newName) { showToast('File name cannot be empty.', 'error'); return; }

    closeModal('edit-doc-modal');
    showUploadOverlay(replaceFile ? 'Replacing file...' : 'Saving changes...');

    try {
        var updates = {
            file_name: newName,
            category: newCategory,
            project_tag: newProject,
            notes: newNotes
        };

        if (replaceFile) {
            var file = fileInput.files[0];
            if (file.size > 100 * 1024 * 1024) {
                hideUploadOverlay();
                showToast('File exceeds 100MB limit.', 'error');
                return;
            }

            // Upload new file to storage
            var newStoragePath = 'teams/' + currentTeam.id + '/docs/' + Date.now() + '_' + file.name;
            var uploadResult = await sb.storage.from('documents').upload(newStoragePath, file);
            if (uploadResult.error) throw uploadResult.error;

            // Delete old file from storage (best-effort)
            sb.storage.from('documents').remove([oldStoragePath]).catch(function() {});

            updates.storage_path = newStoragePath;
            updates.file_type = file.type || 'application/' + file.name.split('.').pop().toLowerCase();
            updates.file_size = file.size;
        }

        // Update document record in DB
        var updateResult = await sb.from('documents').update(updates).eq('id', docId);
        if (updateResult.error) throw updateResult.error;

        hideUploadOverlay();
        showToast('Document updated.');

        // Reload documents list
        await loadDocuments();
        loadHome();

        // Re-index for AI search if file was replaced
        if (replaceFile) {
            try {
                var session = (await sb.auth.getSession()).data.session;
                if (session) {
                    fetch(BACKEND_URL + '/index-document', {
                        method: 'POST',
                        headers: { 'Authorization': 'Bearer ' + session.access_token, 'Content-Type': 'application/json' },
                        body: JSON.stringify({ document_id: docId, storage_path: updates.storage_path })
                    }).catch(function() {});
                }
            } catch (_) {}
        }
    } catch (err) {
        console.error('Edit error:', err);
        hideUploadOverlay();
        showToast('Failed to update document: ' + (err.message || 'Unknown error'), 'error');
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
            name = ((m.first_name || '') + ' ' + (m.last_name || '')).trim() || 'Pending';
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
    var usedEl = document.getElementById('seat-used');
    var maxEl = document.getElementById('seat-max');
    var barEl = document.getElementById('seat-bar-fill');
    if (usedEl) usedEl.textContent = usedSeats;
    if (maxEl) maxEl.textContent = maxSeats;
    if (barEl) barEl.style.width = Math.round((usedSeats / maxSeats) * 100) + '%';
}

async function handleInvite() {
    var firstNameInput = document.getElementById('invite-first-name');
    var lastNameInput = document.getElementById('invite-last-name');
    var emailInput = document.getElementById('invite-email');
    var roleSelect = document.getElementById('invite-role');
    var firstName = firstNameInput.value.trim();
    var lastName = lastNameInput.value.trim();
    var email = emailInput.value.trim().toLowerCase();
    var role = roleSelect.value;

    if (!firstName || !lastName) {
        showToast('Please enter the team member\'s name.', 'error');
        return;
    }
    if (!email) {
        showToast('Please enter an email address.', 'error');
        return;
    }

    var usedSeats = teamMembers.filter(function(m) { return m.status === 'active' || m.status === 'invited'; }).length;
    var maxSeats = currentTeam.max_seats || 10;

    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        // Auto-add a seat if at the limit
        if (usedSeats >= maxSeats) {
            showToast('Adding an extra seat to your plan...');
            var seatResp = await fetch('/.netlify/functions/update-seats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                body: JSON.stringify({ action: 'add', count: 1 })
            });
            var seatData = await seatResp.json();
            if (!seatResp.ok) {
                showToast(seatData.error || 'Failed to add seat.', 'error');
                return;
            }
            // Update local team data
            if (currentTeam) currentTeam.max_seats = seatData.newSeatCount;
        }

        // Insert the team member
        var result = await sb.from('team_members').insert({
            team_id: currentTeam.id,
            first_name: firstName,
            last_name: lastName,
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

        // Send invite email
        var inviterName = currentUser?.user_metadata?.first_name || '';
        fetch('/.netlify/functions/send-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ to: email, template: 'invite', args: [email, currentTeam.name || '', inviterName] })
        }).catch(function(err) { console.error('Invite email error:', err); });

        showToast('Invite sent to ' + firstName + ' (' + email + ').');
        closeModal('add-member-modal');
        firstNameInput.value = '';
        lastNameInput.value = '';
        emailInput.value = '';
        roleSelect.value = 'technician';

        await loadTeam();
        loadHome();
    } catch (err) {
        console.error('Invite error:', err);
        showToast('Failed to add team member: ' + err.message, 'error');
    }
}

var pendingChangeRoleMemberId = null;

function promptChangeRole(memberId, currentRole) {
    pendingChangeRoleMemberId = memberId;
    var select = document.getElementById('change-role-select');
    if (select) select.value = currentRole;
    openModal('change-role-modal');
}

function confirmChangeRole() {
    var memberId = pendingChangeRoleMemberId;
    var select = document.getElementById('change-role-select');
    var newRole = select ? select.value : null;
    closeModal('change-role-modal');
    pendingChangeRoleMemberId = null;
    if (!memberId || !newRole) return;
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
    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;
        var inviterName = currentUser?.user_metadata?.first_name || '';
        await fetch('/.netlify/functions/send-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ to: email, template: 'invite', args: [email, currentTeam.name || '', inviterName] })
        });
        showToast('Invite resent to ' + email + '.');
    } catch (err) {
        console.error('Resend invite error:', err);
        showToast('Failed to resend invite.', 'error');
    }
}

// ============================================
// PER-TECH ACTIVITY
// ============================================

async function loadPerTechActivity() {
    var tbody = document.getElementById('pertech-tbody');
    if (!tbody) return;

    // Get active team members
    var activeMembers = teamMembers.length > 0 ? teamMembers : [];
    if (activeMembers.length === 0) {
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

    // Get query counts per user for this team
    var queryCounts = {};
    var lastQueryDates = {};
    try {
        var qResult = await sb.from('queries')
            .select('user_id, created_at')
            .eq('team_id', currentTeam.id)
            .order('created_at', { ascending: false });
        if (qResult.data) {
            qResult.data.forEach(function(q) {
                queryCounts[q.user_id] = (queryCounts[q.user_id] || 0) + 1;
                if (!lastQueryDates[q.user_id]) lastQueryDates[q.user_id] = q.created_at;
            });
        }
    } catch (_) { /* queries table may not exist yet */ }

    // Get document counts per user for this team
    var docCounts = {};
    try {
        var dResult = await sb.from('documents')
            .select('uploaded_by')
            .eq('team_id', currentTeam.id);
        if (dResult.data) {
            dResult.data.forEach(function(d) {
                docCounts[d.uploaded_by] = (docCounts[d.uploaded_by] || 0) + 1;
            });
        }
    } catch (_) { /* ignore */ }

    tbody.innerHTML = activeMembers.filter(function(m) { return m.status === 'active'; }).map(function(m) {
        var name = m.users ? ((m.users.first_name || '') + ' ' + (m.users.last_name || '')).trim() : m.email;
        var uid = m.user_id;
        var qCount = queryCounts[uid] || 0;
        var dCount = docCounts[uid] || 0;
        var lastDate = lastQueryDates[uid] ? timeAgo(new Date(lastQueryDates[uid])) : '—';
        return '<tr>' +
            '<td class="td-name"><a href="#" class="drill-link" onclick="openDrillPanelForTech(\'' + m.id + '\',\'' + escapeHtml(name) + '\',\'' + uid + '\'); return false;">' + escapeHtml(name) + '</a></td>' +
            '<td>' + qCount + '</td>' +
            '<td>' + lastDate + '</td>' +
            '<td>' + dCount + '</td>' +
            '</tr>';
    }).join('');
}

async function openDrillPanelForTech(memberId, name, userId) {
    var panel = document.getElementById('drill-panel');
    var overlay = document.getElementById('drill-overlay');
    var title = document.getElementById('drill-title');
    var sub = document.getElementById('drill-sub');
    var searchInput = document.getElementById('drill-search-input');
    var list = document.getElementById('drill-list');

    searchInput.value = '';
    title.textContent = name;
    sub.textContent = 'Loading...';
    list.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-light);">Loading queries...</div>';

    panel.classList.add('open');
    overlay.classList.add('open');

    // Fetch real queries for this user
    try {
        var qResult = await sb.from('queries')
            .select('id, question, source, confidence, has_image, created_at')
            .eq('team_id', currentTeam.id)
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(50);

        var queries = qResult.data || [];
        sub.textContent = queries.length + ' quer' + (queries.length === 1 ? 'y' : 'ies') + ' total';

        if (queries.length === 0) {
            list.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-light);">No queries yet. Queries will appear here once ' + escapeHtml(name) + ' uses Arrival in the field.</div>';
            return;
        }

        // Store for search filtering
        if (typeof currentDrillItems !== 'undefined') currentDrillItems = queries;

        list.innerHTML = queries.map(function(q) {
            var shortQ = q.question.length > 80 ? q.question.substring(0, 77) + '...' : q.question;
            var badge = q.has_image ? ' 📷' : '';
            return '<div class="drill-item" style="padding:12px 16px;border-bottom:1px solid var(--border,#e8e4df);">' +
                '<div style="font-weight:500;color:var(--text-dark,#2a2622);">' + escapeHtml(shortQ) + badge + '</div>' +
                '<div style="font-size:12px;color:var(--text-muted,#7c736a);margin-top:4px;">' + timeAgo(new Date(q.created_at)) +
                (q.confidence ? ' · ' + q.confidence + ' confidence' : '') +
                (q.source ? ' · ' + q.source : '') + '</div></div>';
        }).join('');
    } catch (err) {
        console.error('Drill panel query error:', err);
        sub.textContent = '0 queries';
        list.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-light);">Could not load queries.</div>';
    }
}

// ============================================
// SUBSCRIPTION & BILLING
// ============================================

function loadBilling() {
    var seatCount = teamMembers.filter(function(m) { return m.status === 'active' || m.status === 'invited'; }).length;
    var maxSeats = currentTeam ? (currentTeam.max_seats || 10) : 10;
    var extraSeats = Math.max(0, maxSeats - 10);
    var extraCost = extraSeats * 200;
    var total = 200 + extraCost;

    document.getElementById('billing-plan-name').textContent = 'Business Plan';
    document.getElementById('billing-plan-price').textContent = '$200/month';
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

function handleAddSeats() {
    document.getElementById('add-seats-count').value = '1';
    openModal('add-seats-modal');
}

async function confirmAddSeats() {
    var count = parseInt(document.getElementById('add-seats-count').value, 10);
    if (!count || count < 1) { showToast('Enter a valid number.', 'error'); return; }
    closeModal('add-seats-modal');

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

function handleRemoveSeats() {
    document.getElementById('remove-seats-count').value = '1';
    openModal('remove-seats-modal');
}

async function confirmRemoveSeats() {
    var count = parseInt(document.getElementById('remove-seats-count').value, 10);
    if (!count || count < 1) { showToast('Enter a valid number.', 'error'); return; }
    closeModal('remove-seats-modal');

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
        // 1. Clean up Pinecone vectors by deleting each document through the backend API
        var session = (await sb.auth.getSession()).data.session;
        var token = session ? session.access_token : null;
        var teamDocsResult = await sb.from('documents')
            .select('id')
            .eq('team_id', currentTeam.id);
        var personalDocsResult = await sb.from('documents')
            .select('id')
            .eq('uploaded_by', currentUser.id)
            .is('team_id', null);
        var allDocs = [].concat(teamDocsResult.data || [], personalDocsResult.data || []);
        if (allDocs.length > 0 && token) {
            for (var i = 0; i < allDocs.length; i++) {
                try {
                    await fetch(BACKEND_URL + '/documents/' + encodeURIComponent(allDocs[i].id), {
                        method: 'DELETE',
                        headers: { 'Authorization': 'Bearer ' + token }
                    });
                } catch (_) { /* best-effort vector cleanup */ }
            }
        }

        // 2. Delete all team files from storage
        var listResult = await sb.storage.from('documents').list('teams/' + currentTeam.id);
        if (listResult.data && listResult.data.length > 0) {
            var paths = listResult.data.map(function(f) { return 'teams/' + currentTeam.id + '/' + f.name; });
            await sb.storage.from('documents').remove(paths);
        }

        // 3. Delete personal files
        var personalResult = await sb.storage.from('documents').list(currentUser.id);
        if (personalResult.data && personalResult.data.length > 0) {
            var personalPaths = personalResult.data.map(function(f) { return currentUser.id + '/' + f.name; });
            await sb.storage.from('documents').remove(personalPaths);
        }

        // 4. Delete auth user via RPC (cascades to all DB rows)
        var rpcResult = await sb.rpc('delete_own_account');
        if (rpcResult.error) throw rpcResult.error;

        // 5. Sign out and redirect
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

function escapeAttr(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/'/g, '&#39;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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

    // Edit document save button
    document.getElementById('edit-doc-save-btn').addEventListener('click', handleEditDocSave);

    // Invite team member
    document.getElementById('invite-send-btn').addEventListener('click', handleInvite);

    // Remove team member confirm
    document.getElementById('remove-confirm-btn').addEventListener('click', handleRemoveMember);

    // Delete document confirm
    document.getElementById('delete-doc-confirm-btn').addEventListener('click', confirmDeleteDocument);

    // Change role confirm
    document.getElementById('change-role-confirm-btn').addEventListener('click', confirmChangeRole);

    // Company profile save
    document.getElementById('settings-company-save-btn').addEventListener('click', handleSaveCompanyProfile);

    // Personal profile save
    document.getElementById('settings-profile-save-btn').addEventListener('click', handleSavePersonalProfile);

    // Password update
    document.getElementById('settings-password-btn').addEventListener('click', handleUpdatePassword);

    // Delete account
    document.getElementById('delete-confirm-btn').addEventListener('click', handleDeleteAccount);

    // Billing — Remove seats (add seats is now handled via Add Team Member)
    var removeSeatsBtn = document.getElementById('billing-remove-seats-btn');
    if (removeSeatsBtn) removeSeatsBtn.addEventListener('click', handleRemoveSeats);
    var removeSeatsConfirmBtn = document.getElementById('remove-seats-confirm-btn');
    if (removeSeatsConfirmBtn) removeSeatsConfirmBtn.addEventListener('click', confirmRemoveSeats);

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

    // Kill browser autofill on search input — set readonly so browser skips it,
    // then remove readonly on first interaction
    var docSearch = document.getElementById('doc-search');
    if (docSearch) {
        docSearch.setAttribute('readonly', '');
        docSearch.value = '';
        docSearch.addEventListener('focus', function() {
            this.removeAttribute('readonly');
        });
        docSearch.addEventListener('click', function() {
            this.removeAttribute('readonly');
        });
        // Also clear after delays in case browser fills it before our listener
        setTimeout(function() { docSearch.value = ''; }, 100);
        setTimeout(function() { docSearch.value = ''; }, 500);
        setTimeout(function() { docSearch.value = ''; }, 2000);
    }
});

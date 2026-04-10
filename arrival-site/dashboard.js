// ============================================
// ARRIVAL DASHBOARD - dashboard.js
// Supabase backend wiring for individual dashboard
// ============================================

const SUPABASE_URL = 'https://nmmmrujtfrxrmajuggki.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tbW1ydWp0ZnJ4cm1hanVnZ2tpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1Mjk4NzEsImV4cCI6MjA4NzEwNTg3MX0.XaOQaqN_vbYSBeYFol63OzQFuKQYJ_pLXhMX7bvLAJQ';
const BACKEND_URL = 'https://arrival-backend-81x7.onrender.com/api';

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: { lock: function(_name, _acquireTimeout, fn) { return fn(); } }
});

// Current user state
let currentUser = null;
let currentProfile = null;
let currentSubscription = null;

// Document limits by plan
const DOC_LIMITS = { pro: 50, business: 999, enterprise: 999 };
const PLAN_PRICES = { pro: '$20/month', business: '$200/month', enterprise: 'Custom' };

// Category display labels
var CATEGORY_LABELS = {
    manufacturer_manuals: 'Manufacturer Manuals',
    equipment_spec_sheets: 'Equipment Spec Sheets',
    company_sops: 'Company SOPs',
    safety_protocols: 'Safety Protocols',
    diagnostic_workflows: 'Diagnostic Workflows',
    training_materials: 'Training Materials',
    building_plans: 'Building Plans',
    parts_lists: 'Parts Lists',
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
// AUTH GUARD
// ============================================

async function initAuth() {
    var result = await sb.auth.getSession();
    if (!result.data.session) {
        window.location.href = '/?login=true&redirect=' + encodeURIComponent(window.location.pathname + window.location.hash);
        return;
    }
    currentUser = result.data.session.user;
    await loadProfile();

    // Redirect business users to the business dashboard
    // Only redirect if not already bounced back (prevents infinite loop)
    var plan = currentProfile ? currentProfile.account_type : 'pro';
    if (plan === 'business' && !window.location.search.includes('stay=true')) {
        window.location.href = '/dashboard-business';
        return;
    }

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

    loadDocuments();
    loadChatHistory();
    loadSavedAnswers();
    loadBilling();
    loadSettings();
    checkCheckoutSuccess();
}

function showTrialExpiredOverlay() {
    var overlay = document.getElementById('trial-expired-overlay');
    if (overlay) overlay.style.display = 'flex';
}

async function loadProfile() {
    var result = await sb.from('users').select('*').eq('id', currentUser.id).single();
    if (result.data) currentProfile = result.data;

    var subResult = await sb.from('subscriptions').select('*').eq('user_id', currentUser.id).in('status', ['active', 'trial_expired']).limit(1).single();
    if (subResult.data) currentSubscription = subResult.data;
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
// MY DOCUMENTS
// ============================================

var cachedDocs = [];

async function loadDocuments() {
    var result = await sb
        .from('documents')
        .select('*')
        .eq('uploaded_by', currentUser.id)
        .is('team_id', null)
        .not('category', 'in', '("photo","video")')
        .order('created_at', { ascending: false });

    var docs = result.data || [];
    cachedDocs = docs;
    var plan = currentProfile ? currentProfile.account_type : 'pro';
    var limit = DOC_LIMITS[plan] || 50;
    var tbody = document.getElementById('documents-tbody');

    if (docs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted,#7c736a);padding:32px;">No documents uploaded yet.</td></tr>';
    } else {
        // Get signed URLs for image-type documents (for thumbnails)
        var imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
        var imageDocs = docs.filter(function(d) {
            var ext = d.file_name.split('.').pop().toLowerCase();
            return imageExts.indexOf(ext) !== -1;
        });
        var thumbUrls = {};
        if (imageDocs.length > 0) {
            var paths = imageDocs.map(function(d) { return d.storage_path; });
            var signedResults = await sb.storage.from('documents').createSignedUrls(paths, 3600);
            if (signedResults.data) {
                signedResults.data.forEach(function(r) {
                    if (r.signedUrl) thumbUrls[r.path] = r.signedUrl;
                });
            }
        }

        tbody.innerHTML = docs.map(function(d) {
            var ext = d.file_name.split('.').pop().toLowerCase();
            var extUpper = ext.toUpperCase();
            var date = new Date(d.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            var statusClass, statusLabel;
            if (d.status === 'indexed' || d.status === 'ready') {
                statusClass = 'status-ready'; statusLabel = 'Ready';
            } else if (d.status === 'index_failed') {
                statusClass = 'status-failed'; statusLabel = 'Index failed';
            } else {
                statusClass = 'status-processing'; statusLabel = 'Indexing… <span class="info-tip" title="Your document is being read and indexed so Arrival can reference it when answering questions. This usually takes 1–5 minutes depending on file size.">ⓘ</span>';
            }
            var catLabel = CATEGORY_LABELS[d.category] || d.category || '—';
            var catFilter = CATEGORY_FILTERS[d.category] || 'other';
            var project = d.project || d.notes || '—';

            // Build thumbnail
            var thumb;
            if (thumbUrls[d.storage_path]) {
                thumb = '<div class="doc-thumb"><img src="' + thumbUrls[d.storage_path] + '" alt=""></div>';
            } else if (ext === 'pdf') {
                thumb = '<div class="doc-thumb doc-thumb-pdf"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#c45a3c" stroke-width="1.5" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span class="doc-thumb-label">PDF</span></div>';
            } else {
                thumb = '<div class="doc-thumb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9a9590" stroke-width="1.5" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span class="doc-thumb-label">' + extUpper + '</span></div>';
            }

            return '<tr data-cat="' + catFilter + '">' +
                '<td class="td-name"><div class="doc-name-cell">' + thumb + '<span>' + escapeHtml(d.file_name) + '</span></div></td>' +
                '<td><span class="cat-pill">' + escapeHtml(catLabel) + '</span></td>' +
                '<td>' + escapeHtml(project) + '</td>' +
                '<td><span class="' + statusClass + '">' + statusLabel + '</span></td>' +
                '<td>' + date + '</td>' +
                '<td><a href="#" class="table-action" onclick="viewDocument(\'' + escapeAttr(d.id) + '\',\'' + escapeAttr(d.storage_path) + '\'); return false;">View</a> ' +
                '<a href="#" class="table-action" onclick="openEditDocument(\'' + escapeAttr(d.id) + '\'); return false;">Edit</a> ' +
                (d.status === 'index_failed' ? '<a href="#" class="table-action" onclick="retryIndexDocument(\'' + escapeAttr(d.id) + '\',\'' + escapeAttr(d.storage_path) + '\'); return false;">Retry</a> ' : '') +
                '<a href="#" class="table-action table-action-danger" onclick="deleteDocument(\'' + escapeAttr(d.id) + '\',\'' + escapeAttr(d.storage_path) + '\'); return false;">Delete</a></td>' +
                '</tr>';
        }).join('');
    }

    // Update count
    document.getElementById('storage-indicator').innerHTML =
        docs.length + ' / ' + limit + ' documents used <span id="plan-badge" class="plan-badge">' + capitalize(plan) + '</span>';

    // Auto-poll if any docs are still processing
    var hasProcessing = docs.some(function(d) { return d.status !== 'indexed' && d.status !== 'ready' && d.status !== 'index_failed'; });
    if (hasProcessing && !window._docAutoRefresh) {
        window._docAutoRefresh = setInterval(function() {
            loadDocuments();
        }, 10000);
    } else if (!hasProcessing && window._docAutoRefresh) {
        clearInterval(window._docAutoRefresh);
        window._docAutoRefresh = null;
    }

    // Gate uploads if limit reached
    var uploadZone = document.getElementById('upload-zone');
    if (docs.length >= limit) {
        uploadZone.innerHTML = '<svg width="48" height="48" fill="none" stroke="#9a9590" stroke-width="1.5"><path d="M24 32V16M16 22l8-8 8 8"/><rect x="4" y="4" width="40" height="40" rx="8"/></svg>' +
            '<p class="upload-text">Document limit reached</p>' +
            '<p class="upload-formats">Upgrade your plan to upload more documents.</p>';
        uploadZone.onclick = null;
        uploadZone.style.cursor = 'default';
    }
}

// Search documents
function searchDocs(query) {
    var q = query.toLowerCase();
    document.querySelectorAll('#doc-table tbody tr').forEach(function(row) {
        var text = row.textContent.toLowerCase();
        row.style.display = (!q || text.includes(q)) ? '' : 'none';
    });
}

// Poll Supabase every 8s until doc status flips from 'processing' — then refresh the table.
function _pollUntilIndexed(docId) {
    var deadline = Date.now() + 10 * 60 * 1000;
    function check() {
        if (Date.now() > deadline) return;
        sb.from('documents').select('status').eq('id', docId).single().then(function(result) {
            var status = result.data && result.data.status;
            if (status === 'indexed' || status === 'index_failed') {
                loadDocuments();
                if (status === 'indexed') showToast('Document ready — AI can now use it.');
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

    var files = fileInput.files;
    if (!files || files.length === 0) {
        showToast('Please select a file.', 'error');
        return;
    }

    var category = categorySelect.value;
    if (!category) {
        showToast('Please select a category.', 'error');
        return;
    }

    closeModal('upload-modal');

    var total = files.length;
    var uploaded = 0;
    var failed = 0;

    for (var i = 0; i < files.length; i++) {
        var file = files[i];
        if (file.size > 100 * 1024 * 1024) {
            failed++;
            showToast(file.name + ' exceeds 100MB limit.', 'error');
            continue;
        }

        showUploadOverlay('Uploading' + (total > 1 ? ' ' + (i + 1) + ' of ' + total : ' ' + file.name) + '...');

        try {
            // Upload via backend — it stores the file AND kicks off indexing automatically
            var session = (await sb.auth.getSession()).data.session;
            if (!session) throw new Error('Not authenticated');

            var formData = new FormData();
            formData.append('file', file);
            formData.append('category', category);
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
            uploaded++;

            // Poll until indexed (backend fires background task automatically)
            var docId = uploadData.id;
            var storagePath = uploadData.storage_path;
            _pollUntilIndexed(docId, storagePath);

        } catch (err) {
            console.error('Upload error:', err);
            failed++;
            showToast('Failed to upload ' + file.name + ': ' + (err.message || 'Unknown error'), 'error');
        }
    }

    hideUploadOverlay();

    if (uploaded > 0) showToast(uploaded + ' document' + (uploaded > 1 ? 's' : '') + ' uploaded — indexing in background.');
    if (failed > 0) showToast(failed + ' failed.', 'error');

    // Reset modal fields
    fileInput.value = '';
    categorySelect.value = '';
    projectInput.value = '';
    notesInput.value = '';

    await loadDocuments();
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
    } catch (err) {
        console.error('Delete error:', err);
        showToast('Failed to delete document.', 'error');
    }
}

function openEditDocument(docId) {
    var doc = cachedDocs.find(function(d) { return d.id === docId; });
    if (!doc) { showToast('Document not found.', 'error'); return; }

    document.getElementById('edit-doc-id').value = doc.id;
    document.getElementById('edit-doc-storage-path').value = doc.storage_path;
    document.getElementById('edit-doc-name').value = doc.file_name;
    document.getElementById('edit-doc-category').value = doc.category;
    document.getElementById('edit-doc-project').value = doc.project_tag || doc.notes || '';
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
            if (file.size > 50 * 1024 * 1024) {
                hideUploadOverlay();
                showToast('File exceeds 50MB limit.', 'error');
                return;
            }

            // Upload new file to storage
            var newStoragePath = currentUser.id + '/' + Date.now() + '_' + file.name;
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
// CHAT HISTORY
// ============================================

async function loadChatHistory() {
    if (!currentUser) return;
    try {
        var { data: convs, error } = await sb.from('conversations')
            .select('id, title, trade, created_at, updated_at')
            .eq('user_id', currentUser.id)
            .order('updated_at', { ascending: false })
            .limit(50);

        if (error) throw error;

        var tbody = document.getElementById('chat-history-tbody');
        if (!tbody) return;

        if (!convs || convs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted,#7c736a);padding:32px;">No conversations yet. Start using Arrival to see your chat history here.</td></tr>';
            return;
        }

        // Fetch the first user message from each conversation for preview
        var convIds = convs.map(function(c) { return c.id; });
        var { data: msgs } = await sb.from('messages')
            .select('conversation_id, content, role')
            .in('conversation_id', convIds)
            .eq('role', 'user')
            .order('timestamp', { ascending: true });

        // Group first user message per conversation
        var firstMsg = {};
        if (msgs) {
            msgs.forEach(function(m) {
                if (!firstMsg[m.conversation_id]) {
                    firstMsg[m.conversation_id] = m.content;
                }
            });
        }

        tbody.innerHTML = convs.map(function(c) {
            var date = new Date(c.updated_at || c.created_at);
            var dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            var preview = firstMsg[c.id] || c.title || 'Conversation';
            if (preview.length > 80) preview = preview.substring(0, 80) + '...';
            var trade = c.trade ? capitalize(c.trade.replace(/_/g, ' ')) : '—';
            return '<tr>' +
                '<td style="white-space:nowrap;">' + escapeHtml(dateStr) + '</td>' +
                '<td>' + escapeHtml(preview) + '</td>' +
                '<td>' + escapeHtml(trade) + '</td>' +
                '</tr>';
        }).join('');

    } catch (err) {
        console.error('loadChatHistory error:', err);
    }
}


// ============================================
// SAVED ANSWERS
// ============================================

async function loadSavedAnswers() {
    if (!currentUser) return;
    try {
        var { data: answers, error } = await sb.from('saved_answers')
            .select('id, question, answer, trade, created_at')
            .eq('user_id', currentUser.id)
            .order('created_at', { ascending: false })
            .limit(50);

        if (error) {
            // Table may not exist yet — not a critical failure
            console.warn('loadSavedAnswers:', error.message);
            return;
        }

        var tbody = document.getElementById('saved-answers-tbody');
        if (!tbody) return;

        if (!answers || answers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted,#7c736a);padding:32px;">No saved answers yet. Bookmark answers in the Arrival app to see them here.</td></tr>';
            return;
        }

        tbody.innerHTML = answers.map(function(a) {
            var question = a.question || 'Saved answer';
            if (question.length > 80) question = question.substring(0, 80) + '...';
            var date = new Date(a.created_at);
            var dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            var trade = a.trade ? capitalize(a.trade.replace(/_/g, ' ')) : '—';
            return '<tr>' +
                '<td>' + escapeHtml(question) + '</td>' +
                '<td style="white-space:nowrap;">' + escapeHtml(dateStr) + '</td>' +
                '<td>' + escapeHtml(trade) + '</td>' +
                '</tr>';
        }).join('');

    } catch (err) {
        console.error('loadSavedAnswers error:', err);
    }
}


// ============================================
// SUBSCRIPTION & BILLING
// ============================================

// Stripe Elements state
var stripeInstance = null;
var cardElement = null;
var setupClientSecret = null;

function loadBilling() {
    var plan = currentSubscription ? currentSubscription.plan : 'pro';
    var isOnTrial = currentSubscription && currentSubscription.trial_ends_at && !currentSubscription.stripe_subscription_id;

    // Billing detail text
    var detailEl = document.getElementById('billing-plan-detail');
    var trialBanner = document.getElementById('trial-banner');
    if (isOnTrial) {
        var daysLeft = 0;
        var trialEnd = new Date(currentSubscription.trial_ends_at);
        daysLeft = Math.ceil((trialEnd - new Date()) / 86400000);
        if (daysLeft < 0) daysLeft = 0;

        if (daysLeft > 0) {
            detailEl.textContent = 'You are on a 7-day trial of the ' + capitalize(plan) + ' plan. Add a payment method below to keep access.';
            if (trialBanner) {
                trialBanner.style.display = 'flex';
                var daysEl = document.getElementById('trial-days-left');
                if (daysEl) daysEl.textContent = daysLeft;
                trialBanner.className = 'trial-banner' + (daysLeft <= 1 ? ' trial-red' : daysLeft <= 3 ? ' trial-orange' : '');
            }
        } else {
            detailEl.textContent = 'Your trial has ended. Subscribe below to continue using Arrival.';
            if (trialBanner) {
                trialBanner.style.display = 'flex';
                trialBanner.className = 'trial-banner trial-red';
                trialBanner.innerHTML = '<div class="trial-banner-text"><strong>Trial expired</strong> — subscribe now to keep using Arrival.</div>';
            }
        }
    } else if (currentSubscription && currentSubscription.current_period_end) {
        var endDate = new Date(currentSubscription.current_period_end);
        detailEl.textContent = 'You are on the ' + capitalize(plan) + ' plan. Next billing date: ' + endDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    } else {
        detailEl.textContent = 'You are on the ' + capitalize(plan) + ' plan. Choose a plan below to change your subscription.';
    }

    // Highlight current plan card
    var cards = ['pro', 'business', 'enterprise'];
    cards.forEach(function(p) {
        var card = document.getElementById('plan-card-' + p);
        if (card) card.classList.toggle('plan-active', p === plan);
    });

    // Update button states for each plan card
    var btnPro = document.getElementById('billing-btn-pro');
    var btnBiz = document.getElementById('billing-btn-biz');

    if (plan === 'pro') {
        btnPro.textContent = isOnTrial ? 'Subscribe to Pro' : 'Current Plan';
        btnPro.disabled = !isOnTrial;
        btnPro.className = isOnTrial ? 'btn btn-primary' : 'btn btn-outline';
        btnBiz.textContent = 'Upgrade to Business';
        btnBiz.disabled = false;
        btnBiz.className = 'btn btn-primary';
    } else if (plan === 'business') {
        btnPro.textContent = 'Downgrade';
        btnPro.disabled = true;
        btnPro.className = 'btn btn-outline';
        btnBiz.textContent = 'Current Plan';
        btnBiz.disabled = true;
        btnBiz.className = 'btn btn-outline';
    }

    // Show cancel + payment + invoice sections for paying users
    var hasPaidSub = currentSubscription && currentSubscription.stripe_subscription_id;
    var cancelSection = document.getElementById('billing-cancel-section');
    if (cancelSection) cancelSection.style.display = hasPaidSub ? '' : 'none';

    document.getElementById('billing-payment-section').style.display = hasPaidSub ? '' : 'none';
    document.getElementById('billing-invoice-section').style.display = hasPaidSub ? '' : 'none';

    // Load billing details from Stripe
    if (hasPaidSub) {
        loadBillingDetails();
    }
}

async function loadBillingDetails() {
    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        var response = await fetch('/.netlify/functions/get-billing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({})
        });

        var data = await response.json();
        if (!response.ok) {
            console.error('Get billing error:', data.error);
            return;
        }

        // Render payment method
        renderPaymentMethod(data.paymentMethod);

        // Render invoices
        renderInvoices(data.invoices || []);

    } catch (err) {
        console.error('Load billing details error:', err);
    }
}

function renderPaymentMethod(pm) {
    var infoEl = document.getElementById('payment-method-info');
    var changeBtn = document.getElementById('change-card-btn');

    if (pm && pm.last4) {
        var brandClass = 'card-brand-default';
        var brandLabel = pm.brand ? pm.brand.toUpperCase() : 'CARD';
        if (pm.brand === 'visa') brandClass = 'card-brand-visa';
        else if (pm.brand === 'mastercard') brandClass = 'card-brand-mastercard';
        else if (pm.brand === 'amex') brandClass = 'card-brand-amex';
        else if (pm.brand === 'discover') brandClass = 'card-brand-discover';

        var expStr = (pm.expMonth < 10 ? '0' : '') + pm.expMonth + '/' + pm.expYear;
        infoEl.innerHTML = '<span class="card-brand-badge ' + brandClass + '">' + escapeHtml(brandLabel) + '</span>' +
            '<div class="card-details">' +
            '<span class="card-number">&bull;&bull;&bull;&bull; &bull;&bull;&bull;&bull; &bull;&bull;&bull;&bull; ' + escapeHtml(pm.last4) + '</span>' +
            '<span class="card-expiry">Expires ' + expStr + '</span>' +
            '</div>';
        changeBtn.style.display = '';
    } else {
        infoEl.innerHTML = '<span style="color:var(--text-muted);">No payment method on file.</span>';
        changeBtn.style.display = '';
        changeBtn.textContent = 'Add Card';
    }
}

function renderInvoices(invoices) {
    var wrapper = document.getElementById('invoice-list-wrapper');

    if (!invoices || invoices.length === 0) {
        wrapper.innerHTML = '<p style="color:var(--text-muted);font-size:14px;">No invoices yet.</p>';
        return;
    }

    var rows = invoices.map(function(inv) {
        var date = new Date(inv.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        var statusHtml = inv.status === 'paid'
            ? '<span class="status-paid">Paid</span>'
            : '<span style="color:var(--text-muted);">' + capitalize(inv.status || 'unknown') + '</span>';
        var downloadHtml = inv.pdf
            ? '<a href="' + inv.pdf + '" target="_blank" class="invoice-download">Download</a>'
            : '—';
        return '<tr>' +
            '<td>' + escapeHtml(inv.number || '—') + '</td>' +
            '<td>' + date + '</td>' +
            '<td>$' + inv.amount + ' ' + inv.currency + '</td>' +
            '<td>' + statusHtml + '</td>' +
            '<td>' + downloadHtml + '</td>' +
            '</tr>';
    }).join('');

    wrapper.innerHTML = '<div class="table-wrapper"><table class="invoice-table">' +
        '<thead><tr><th>Invoice</th><th>Date</th><th>Amount</th><th>Status</th><th></th></tr></thead>' +
        '<tbody>' + rows + '</tbody></table></div>';
}

// ============================================
// STRIPE ELEMENTS — Card Update
// ============================================

function initStripeElements() {
    if (stripeInstance) return;
    if (typeof Stripe === 'undefined') {
        console.error('Stripe.js not loaded');
        return;
    }
    stripeInstance = Stripe('pk_live_51T2waTAO3BMpwX67aWYd3cxZFLJbqCFGjG3GPaVFqNjHQr23e3VxRYkfBavqK4JBGSb5lkkJtpDjITfZS5i2GzpE00jQKw6qlp');
}

async function showCardForm() {
    initStripeElements();
    if (!stripeInstance) return;

    var formDiv = document.getElementById('card-update-form');
    formDiv.style.display = '';

    // Create or re-mount card element
    if (!cardElement) {
        var elements = stripeInstance.elements();
        cardElement = elements.create('card', {
            style: {
                base: {
                    fontSize: '15px',
                    color: '#2a2622',
                    fontFamily: "'DM Sans', sans-serif",
                    '::placeholder': { color: '#9a9590' }
                },
                invalid: { color: '#c45a3c' }
            }
        });
    }
    cardElement.mount('#card-element');

    // Get SetupIntent client secret
    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        var response = await fetch('/.netlify/functions/update-payment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ action: 'create_setup_intent' })
        });

        var data = await response.json();
        if (data.clientSecret) {
            setupClientSecret = data.clientSecret;
        } else {
            showToast(data.error || 'Failed to initialize card form.', 'error');
            formDiv.style.display = 'none';
        }
    } catch (err) {
        console.error('SetupIntent error:', err);
        showToast('Failed to initialize card form.', 'error');
        formDiv.style.display = 'none';
    }
}

async function saveNewCard() {
    if (!stripeInstance || !cardElement || !setupClientSecret) {
        showToast('Card form not ready. Please try again.', 'error');
        return;
    }

    var saveBtn = document.getElementById('save-card-btn');
    saveBtn.classList.add('btn-loading');
    saveBtn.disabled = true;

    try {
        var result = await stripeInstance.confirmCardSetup(setupClientSecret, {
            payment_method: { card: cardElement }
        });

        if (result.error) {
            document.getElementById('card-errors').textContent = result.error.message;
            saveBtn.classList.remove('btn-loading');
            saveBtn.disabled = false;
            return;
        }

        // Set the new payment method as default
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        var response = await fetch('/.netlify/functions/update-payment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ action: 'set_default', paymentMethodId: result.setupIntent.payment_method })
        });

        var data = await response.json();
        if (data.success) {
            showToast('Payment method updated.');
            renderPaymentMethod(data.paymentMethod);
            hideCardForm();
        } else {
            showToast(data.error || 'Failed to update payment method.', 'error');
        }
    } catch (err) {
        console.error('Save card error:', err);
        showToast('Something went wrong. Please try again.', 'error');
    }

    saveBtn.classList.remove('btn-loading');
    saveBtn.disabled = false;
}

function hideCardForm() {
    var formDiv = document.getElementById('card-update-form');
    formDiv.style.display = 'none';
    document.getElementById('card-errors').textContent = '';
    setupClientSecret = null;
    if (cardElement) cardElement.clear();
}

// ============================================
// CANCEL SUBSCRIPTION (in-app)
// ============================================

async function handleCancelSubscription() {
    var cancelBtn = document.getElementById('cancel-confirm-btn');
    cancelBtn.classList.add('btn-loading');
    cancelBtn.disabled = true;

    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        var response = await fetch('/.netlify/functions/cancel-subscription', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({})
        });

        var data = await response.json();
        if (data.success) {
            closeModal('cancel-modal');
            var cancelDate = new Date(data.cancelAt).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
            showToast('Subscription cancelled. Access continues until ' + cancelDate + '.');
            // Update the billing detail text
            var detailEl = document.getElementById('billing-plan-detail');
            detailEl.textContent = 'Your subscription has been cancelled. You have access until ' + cancelDate + '.';
        } else {
            showToast(data.error || 'Failed to cancel subscription.', 'error');
        }
    } catch (err) {
        console.error('Cancel error:', err);
        showToast('Something went wrong. Please try again.', 'error');
    }

    cancelBtn.classList.remove('btn-loading');
    cancelBtn.disabled = false;
}

// ============================================
// ACCOUNT SETTINGS
// ============================================

function loadSettings() {
    if (!currentProfile) return;

    document.getElementById('settings-first-name').value = currentProfile.first_name || '';
    document.getElementById('settings-last-name').value = currentProfile.last_name || '';
    document.getElementById('settings-email').value = currentProfile.email || currentUser.email || '';
    document.getElementById('settings-trade').value = currentProfile.primary_trade || 'hvac';
    document.getElementById('settings-experience').value = currentProfile.experience_level || 'apprentice';

    // Preferences
    var units = currentProfile.preferred_units || 'imperial';
    document.querySelectorAll('#pref-units .toggle-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.getAttribute('data-value') === units);
    });

    var depth = currentProfile.explanation_depth || 'standard';
    document.querySelectorAll('input[name="depth"]').forEach(function(radio) {
        radio.checked = radio.value === depth;
    });

    var voiceSwitch = document.getElementById('pref-voice');
    if (currentProfile.voice_output) {
        voiceSwitch.classList.add('on');
    } else {
        voiceSwitch.classList.remove('on');
    }
}

async function handleSaveProfile() {
    var btn = document.getElementById('settings-save-btn');
    var originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Saving...';
    btn.style.opacity = '0.7';

    var firstName = document.getElementById('settings-first-name').value.trim();
    var lastName = document.getElementById('settings-last-name').value.trim();
    var trade = document.getElementById('settings-trade').value;
    var experience = document.getElementById('settings-experience').value;

    // Preferences
    var unitsBtn = document.querySelector('#pref-units .toggle-btn.active');
    var units = unitsBtn ? unitsBtn.getAttribute('data-value') : 'imperial';

    var depthRadio = document.querySelector('input[name="depth"]:checked');
    var depth = depthRadio ? depthRadio.value : 'standard';

    var voiceOn = document.getElementById('pref-voice').classList.contains('on');

    try {
        var result = await sb.from('users').update({
            first_name: firstName,
            last_name: lastName,
            primary_trade: trade,
            experience_level: experience,
            preferred_units: units,
            explanation_depth: depth,
            voice_output: voiceOn
        }).eq('id', currentUser.id);

        if (result.error) throw result.error;

        currentProfile.first_name = firstName;
        currentProfile.last_name = lastName;
        currentProfile.primary_trade = trade;
        currentProfile.experience_level = experience;
        currentProfile.preferred_units = units;
        currentProfile.explanation_depth = depth;
        currentProfile.voice_output = voiceOn;

        btn.textContent = 'Saved ✓';
        btn.style.background = '#16a34a';
        btn.style.opacity = '1';
        showToast('Profile saved successfully.');
        setTimeout(function() {
            btn.textContent = originalText;
            btn.style.background = '';
            btn.disabled = false;
        }, 2000);
    } catch (err) {
        console.error('Save profile error:', err);
        btn.textContent = originalText;
        btn.style.opacity = '1';
        btn.style.background = '';
        btn.disabled = false;
        showToast('Failed to save profile.', 'error');
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
        var docsResult = await sb.from('documents')
            .select('id')
            .eq('uploaded_by', currentUser.id);
        if (docsResult.data && docsResult.data.length > 0 && token) {
            for (var i = 0; i < docsResult.data.length; i++) {
                try {
                    await fetch(BACKEND_URL + '/documents/' + encodeURIComponent(docsResult.data[i].id), {
                        method: 'DELETE',
                        headers: { 'Authorization': 'Bearer ' + token }
                    });
                } catch (_) { /* best-effort vector cleanup */ }
            }
        }

        // 2. Delete all user files from storage
        var listResult = await sb.storage.from('documents').list(currentUser.id);
        if (listResult.data && listResult.data.length > 0) {
            var paths = listResult.data.map(function(f) { return currentUser.id + '/' + f.name; });
            await sb.storage.from('documents').remove(paths);
        }

        // 3. Delete auth user via RPC (cascades to all DB rows via FK)
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

function showUploadOverlay(text) {
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
// HELPERS
// ============================================

function escapeAttr(str) { if (!str) return ''; return str.replace(/&/g,'&amp;').replace(/'/g,'&#39;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// ============================================
// STRIPE BILLING HELPERS
// ============================================

async function startCheckout(targetPlan) {
    try {
        var session = await sb.auth.getSession();
        var token = session.data.session.access_token;

        showToast('Redirecting to checkout...');
        var response = await fetch('/.netlify/functions/create-checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ plan: targetPlan, userId: currentUser.id, email: currentUser.email })
        });

        var data = await response.json();
        if (data.url) {
            window.location.href = data.url;
        } else {
            showToast(data.error || 'Failed to start checkout.', 'error');
        }
    } catch (err) {
        console.error('Checkout error:', err);
        showToast('Something went wrong. Please try again.', 'error');
    }
}

function checkCheckoutSuccess() {
    if (window.location.search.includes('checkout=success')) {
        var plan = currentSubscription ? currentSubscription.plan : 'pro';
        showToast('Subscription activated! Welcome to ' + capitalize(plan) + '.');
        window.history.replaceState({}, '', window.location.pathname);
    }
}

// ============================================
// DRAG & DROP
// ============================================

function initDragDrop() {
    var zone = document.getElementById('upload-zone');
    if (!zone) return;

    zone.addEventListener('dragover', function(e) {
        e.preventDefault();
        zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', function() {
        zone.classList.remove('drag-over');
    });
    zone.addEventListener('drop', function(e) {
        e.preventDefault();
        zone.classList.remove('drag-over');
        // Open modal and pre-fill file input
        openModal('upload-modal');
        var input = document.getElementById('upload-file-input');
        if (input) input.files = e.dataTransfer.files;
    });
}

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Upload modal submit button
    var uploadBtn = document.getElementById('upload-submit-btn');
    if (uploadBtn) uploadBtn.addEventListener('click', handleDocUpload);

    // Edit document save button
    var editDocBtn = document.getElementById('edit-doc-save-btn');
    if (editDocBtn) editDocBtn.addEventListener('click', handleEditDocSave);

    // Profile save
    document.getElementById('settings-save-btn').addEventListener('click', handleSaveProfile);

    // Password change
    document.getElementById('settings-password-btn').addEventListener('click', handleUpdatePassword);

    // Delete account
    document.getElementById('delete-confirm-btn').addEventListener('click', handleDeleteAccount);

    // Delete document confirm
    var delDocBtn = document.getElementById('delete-doc-confirm-btn');
    if (delDocBtn) delDocBtn.addEventListener('click', confirmDeleteDocument);

    // Billing — Upgrade to Pro
    document.getElementById('billing-btn-pro').addEventListener('click', function() {
        startCheckout('pro');
    });

    // Billing — Upgrade to Business
    document.getElementById('billing-btn-biz').addEventListener('click', function() {
        startCheckout('business');
    });

    // Billing — Cancel subscription (in-app)
    var cancelConfirmBtn = document.getElementById('cancel-confirm-btn');
    if (cancelConfirmBtn) {
        cancelConfirmBtn.addEventListener('click', handleCancelSubscription);
    }

    // Billing — Change/Add Card button
    var changeCardBtn = document.getElementById('change-card-btn');
    if (changeCardBtn) {
        changeCardBtn.addEventListener('click', function() { showCardForm(); });
    }

    // Billing — Save new card
    var saveCardBtn = document.getElementById('save-card-btn');
    if (saveCardBtn) {
        saveCardBtn.addEventListener('click', function() { saveNewCard(); });
    }

    // Billing — Cancel card update
    var cancelCardBtn = document.getElementById('cancel-card-btn');
    if (cancelCardBtn) {
        cancelCardBtn.addEventListener('click', function() { hideCardForm(); });
    }

    // Drag & drop
    initDragDrop();

    // Auth check & load data
    initAuth();
});

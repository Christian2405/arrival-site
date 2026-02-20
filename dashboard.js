// ============================================
// ARRIVAL DASHBOARD - dashboard.js
// Supabase backend wiring for individual dashboard
// ============================================

const SUPABASE_URL = 'https://nmmmrujtfrxrmajuggki.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5tbW1ydWp0ZnJ4cm1hanVnZ2tpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1Mjk4NzEsImV4cCI6MjA4NzEwNTg3MX0.XaOQaqN_vbYSBeYFol63OzQFuKQYJ_pLXhMX7bvLAJQ';

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Current user state
let currentUser = null;
let currentProfile = null;
let currentSubscription = null;

// Document limits by plan
const DOC_LIMITS = { free: 3, pro: 20, business: 50, enterprise: 200 };
const PLAN_PRICES = { free: '$0/month', pro: '$25/month', business: '$79/month', enterprise: 'Custom' };

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
// AUTH GUARD
// ============================================

async function initAuth() {
    var result = await sb.auth.getSession();
    if (!result.data.session) {
        window.location.href = '/';
        return;
    }
    currentUser = result.data.session.user;
    await loadProfile();
    loadDocuments();
    loadMedia();
    loadBilling();
    loadSettings();
}

async function loadProfile() {
    var result = await sb.from('users').select('*').eq('id', currentUser.id).single();
    if (result.data) currentProfile = result.data;

    var subResult = await sb.from('subscriptions').select('*').eq('user_id', currentUser.id).eq('status', 'active').limit(1).single();
    if (subResult.data) currentSubscription = subResult.data;
}

// ============================================
// LOGOUT
// ============================================

async function handleLogout() {
    await sb.auth.signOut();
    window.location.href = '/';
}

// ============================================
// MY DOCUMENTS
// ============================================

async function loadDocuments() {
    var result = await sb
        .from('documents')
        .select('*')
        .eq('uploaded_by', currentUser.id)
        .is('team_id', null)
        .order('created_at', { ascending: false });

    var docs = result.data || [];
    var plan = currentProfile ? currentProfile.account_type : 'free';
    var limit = DOC_LIMITS[plan] || 20;
    var tbody = document.getElementById('documents-tbody');

    if (docs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted,#7c736a);padding:32px;">No documents uploaded yet.</td></tr>';
    } else {
        tbody.innerHTML = docs.map(function(d) {
            var ext = d.file_name.split('.').pop().toUpperCase();
            var date = new Date(d.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            var statusClass = d.status === 'ready' ? 'status-ready' : 'status-processing';
            var statusLabel = d.status.charAt(0).toUpperCase() + d.status.slice(1);
            return '<tr>' +
                '<td class="td-name">' + escapeHtml(d.file_name) + '</td>' +
                '<td>' + ext + '</td>' +
                '<td><span class="' + statusClass + '">' + statusLabel + '</span></td>' +
                '<td>' + date + '</td>' +
                '<td><a href="#" class="table-action" onclick="viewDocument(\'' + d.id + '\',\'' + d.storage_path + '\'); return false;">View</a> ' +
                '<a href="#" class="table-action table-action-danger" onclick="deleteDocument(\'' + d.id + '\',\'' + d.storage_path + '\'); return false;">Delete</a></td>' +
                '</tr>';
        }).join('');
    }

    // Update count
    document.getElementById('storage-indicator').innerHTML =
        docs.length + ' / ' + limit + ' documents used <span id="plan-badge" class="plan-badge">' + capitalize(plan) + '</span>';

    // Gate uploads for free users
    var uploadZone = document.getElementById('upload-zone');
    if (plan === 'free') {
        uploadZone.innerHTML = '<svg width="48" height="48" fill="none" stroke="#9a9590" stroke-width="1.5"><path d="M24 32V16M16 22l8-8 8 8"/><rect x="4" y="4" width="40" height="40" rx="8"/></svg>' +
            '<p class="upload-text">Upgrade to Pro to upload documents</p>' +
            '<p class="upload-formats"><a href="/pricing" style="color:var(--accent,#b5935a);text-decoration:underline;">View plans</a></p>';
        uploadZone.onclick = null;
        uploadZone.style.cursor = 'default';
    } else if (docs.length >= limit) {
        uploadZone.innerHTML = '<svg width="48" height="48" fill="none" stroke="#9a9590" stroke-width="1.5"><path d="M24 32V16M16 22l8-8 8 8"/><rect x="4" y="4" width="40" height="40" rx="8"/></svg>' +
            '<p class="upload-text">Document limit reached</p>' +
            '<p class="upload-formats">Upgrade your plan to upload more documents.</p>';
        uploadZone.onclick = null;
        uploadZone.style.cursor = 'default';
    }
}

async function handleFileUpload(event) {
    var files = event.target.files;
    if (!files || files.length === 0) return;

    var plan = currentProfile ? currentProfile.account_type : 'free';
    if (plan === 'free') {
        showToast('Upgrade to Pro to upload documents.', 'error');
        return;
    }

    var total = files.length;
    var uploaded = 0;
    var failed = 0;

    showUploadOverlay('Uploading ' + total + ' document' + (total > 1 ? 's' : '') + '...');

    for (var i = 0; i < files.length; i++) {
        var file = files[i];
        if (file.size > 50 * 1024 * 1024) {
            failed++;
            showToast(file.name + ' exceeds 50MB limit.', 'error');
            continue;
        }

        if (total > 1) {
            showUploadOverlay('Uploading ' + (i + 1) + ' of ' + total + '...');
        }

        var storagePath = currentUser.id + '/' + Date.now() + '_' + file.name;

        try {
            var uploadResult = await sb.storage.from('documents').upload(storagePath, file);
            if (uploadResult.error) throw uploadResult.error;

            var ext = file.name.split('.').pop().toLowerCase();
            var category = 'equipment_manuals';
            var insertResult = await sb.from('documents').insert({
                uploaded_by: currentUser.id,
                team_id: null,
                file_name: file.name,
                file_type: file.type || 'application/' + ext,
                file_size: file.size,
                storage_path: storagePath,
                category: category,
                status: 'ready'
            });
            if (insertResult.error) throw insertResult.error;

            uploaded++;
        } catch (err) {
            console.error('Upload error:', err);
            failed++;
            showToast('Failed to upload ' + file.name + ': ' + err.message, 'error');
        }
    }

    hideUploadOverlay();

    event.target.value = '';
    await loadDocuments();
}

async function viewDocument(docId, storagePath) {
    try {
        var result = sb.storage.from('documents').getPublicUrl(storagePath);
        // Since bucket is private, we need a signed URL
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
        // Delete from storage
        var storageResult = await sb.storage.from('documents').remove([storagePath]);
        if (storageResult.error) throw storageResult.error;

        // Delete DB row
        var dbResult = await sb.from('documents').delete().eq('id', docId);
        if (dbResult.error) throw dbResult.error;

        showToast('Document deleted.');
        await loadDocuments();
    } catch (err) {
        console.error('Delete error:', err);
        showToast('Failed to delete document.', 'error');
    }
}

// ============================================
// SUBSCRIPTION & BILLING
// ============================================

function loadBilling() {
    var plan = currentSubscription ? currentSubscription.plan : 'free';
    var price = PLAN_PRICES[plan] || '$0/month';

    document.getElementById('billing-plan-name').textContent = capitalize(plan) + ' Plan';
    document.getElementById('billing-plan-price').textContent = price;

    var detailEl = document.getElementById('billing-plan-detail');
    if (currentSubscription && currentSubscription.current_period_end) {
        var endDate = new Date(currentSubscription.current_period_end);
        detailEl.textContent = 'Next billing date: ' + endDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    } else if (plan === 'free') {
        detailEl.textContent = '';
    }

    // Upgrade button text
    var upgradeBtn = document.getElementById('billing-upgrade-btn');
    if (plan === 'free') {
        upgradeBtn.textContent = 'Upgrade to Pro';
    } else if (plan === 'pro') {
        upgradeBtn.textContent = 'Upgrade to Business';
    } else {
        upgradeBtn.textContent = 'Manage Plan';
    }

    // Show cancel button for paid plans
    var cancelBtn = document.getElementById('billing-cancel-btn');
    cancelBtn.style.display = (plan !== 'free') ? '' : 'none';

    // Show payment and invoice sections for paid plans
    document.getElementById('billing-payment-section').style.display = (plan !== 'free') ? '' : 'none';
    document.getElementById('billing-invoice-section').style.display = (plan !== 'free') ? '' : 'none';
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

        showToast('Profile saved.');
    } catch (err) {
        console.error('Save profile error:', err);
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
        // 1. Delete all user files from storage
        var listResult = await sb.storage.from('documents').list(currentUser.id);
        if (listResult.data && listResult.data.length > 0) {
            var paths = listResult.data.map(function(f) { return currentUser.id + '/' + f.name; });
            await sb.storage.from('documents').remove(paths);
        }

        // 2. Delete auth user via RPC (cascades to all DB rows via FK)
        var rpcResult = await sb.rpc('delete_own_account');
        if (rpcResult.error) throw rpcResult.error;

        // 3. Sign out and redirect
        await sb.auth.signOut();
        window.location.href = '/';
    } catch (err) {
        console.error('Delete account error:', err);
        showToast('Failed to delete account: ' + err.message, 'error');
    }
}

// ============================================
// PHOTOS & VIDEOS
// ============================================

var userMedia = [];

async function loadMedia() {
    var result = await sb.from('documents')
        .select('*')
        .eq('uploaded_by', currentUser.id)
        .is('team_id', null)
        .in('category', ['photo', 'video'])
        .order('created_at', { ascending: false });

    userMedia = result.data || [];
    renderMediaGrid(userMedia);

    var plan = currentProfile ? currentProfile.account_type : 'free';
    var indicator = document.getElementById('media-storage-indicator');
    if (indicator) indicator.innerHTML = userMedia.length + ' files uploaded <span class="plan-badge">' + capitalize(plan) + '</span>';
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
        var title = m.notes || m.file_name;

        return '<div class="media-card" data-media="' + mediaType + '">' +
            '<div class="' + thumbClass + '" style="background:#e8e4df;">' + svg + '</div>' +
            '<div class="media-info">' +
                '<div class="media-name">' + escapeHtml(title) + '</div>' +
                '<div class="media-meta">' + ext + ' · ' + sizeMB + ' MB · ' + date + '</div>' +
            '</div>' +
            '<div class="media-actions"><a href="#" class="table-action" onclick="viewMedia(\'' + m.id + '\',\'' + m.storage_path + '\'); return false;">View</a> <a href="#" class="table-action table-action-danger" onclick="deleteMedia(\'' + m.id + '\',\'' + m.storage_path + '\'); return false;">Delete</a></div>' +
            '</div>';
    }).join('');
}

function filterMediaIndiv(el, type) {
    el.parentElement.querySelectorAll('.filter-tab').forEach(function(t) { t.classList.remove('active'); });
    el.classList.add('active');
    document.querySelectorAll('#media-grid .media-card').forEach(function(card) {
        card.style.display = (type === 'all' || card.dataset.media === type) ? '' : 'none';
    });
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

async function handleMediaUpload(event) {
    var files = event.target.files;
    if (!files || files.length === 0) return;

    var total = files.length;
    var uploaded = 0;
    var failed = 0;

    showUploadOverlay('Uploading ' + total + ' file' + (total > 1 ? 's' : '') + '...');

    for (var i = 0; i < files.length; i++) {
        var file = files[i];
        if (file.size > 200 * 1024 * 1024) {
            failed++;
            showToast(file.name + ' exceeds 200MB limit.', 'error');
            continue;
        }

        if (total > 1) {
            showUploadOverlay('Uploading ' + (i + 1) + ' of ' + total + '...');
        }

        var isVideo = file.type.startsWith('video/');
        var category = isVideo ? 'video' : 'photo';
        var safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
        var storagePath = currentUser.id + '/media/' + Date.now() + '_' + safeName;

        try {
            var uploadResult = await sb.storage.from('documents').upload(storagePath, file, {
                cacheControl: '3600',
                upsert: false
            });
            if (uploadResult.error) throw uploadResult.error;

            var ext = file.name.split('.').pop().toLowerCase();
            var insertResult = await sb.from('documents').insert({
                uploaded_by: currentUser.id,
                team_id: null,
                file_name: file.name,
                file_type: file.type || (isVideo ? 'video/' + ext : 'image/' + ext),
                file_size: file.size,
                storage_path: storagePath,
                category: category,
                status: 'ready'
            });
            if (insertResult.error) throw insertResult.error;

            uploaded++;
        } catch (err) {
            console.error('Media upload error:', err);
            failed++;
            showToast('Failed: ' + (err.message || JSON.stringify(err)), 'error');
        }
    }

    hideUploadOverlay();

    event.target.value = '';
    await loadMedia();
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
// HELPERS
// ============================================

function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
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
        var input = document.getElementById('file-input');
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event('change'));
    });
}

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // File upload handler
    document.getElementById('file-input').addEventListener('change', handleFileUpload);

    // Profile save
    document.getElementById('settings-save-btn').addEventListener('click', handleSaveProfile);

    // Password change
    document.getElementById('settings-password-btn').addEventListener('click', handleUpdatePassword);

    // Delete account
    document.getElementById('delete-confirm-btn').addEventListener('click', handleDeleteAccount);

    // Billing buttons — coming soon
    document.getElementById('billing-upgrade-btn').addEventListener('click', function() {
        showToast('Coming soon — upgrade will be available shortly.');
    });
    document.getElementById('cancel-confirm-btn') && document.getElementById('cancel-confirm-btn').addEventListener('click', function() {
        showToast('Coming soon — cancellation will be available shortly.');
        closeModal('cancel-modal');
    });

    // Payment update — coming soon
    var paymentBtns = document.querySelectorAll('#billing-payment-section .btn');
    paymentBtns.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            showToast('Coming soon.');
        });
    });

    // Invoice download — coming soon
    var invoiceLinks = document.querySelectorAll('#billing-invoice-section .table-action');
    invoiceLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            showToast('Coming soon.');
        });
    });

    // Media upload handler
    document.getElementById('media-input').addEventListener('change', handleMediaUpload);

    // Media drag & drop
    var mediaZone = document.getElementById('media-upload-zone');
    if (mediaZone) {
        mediaZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            mediaZone.classList.add('drag-over');
        });
        mediaZone.addEventListener('dragleave', function() {
            mediaZone.classList.remove('drag-over');
        });
        mediaZone.addEventListener('drop', function(e) {
            e.preventDefault();
            mediaZone.classList.remove('drag-over');
            var input = document.getElementById('media-input');
            input.files = e.dataTransfer.files;
            input.dispatchEvent(new Event('change'));
        });
    }

    // Drag & drop
    initDragDrop();

    // Auth check & load data
    initAuth();
});

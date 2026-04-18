/* =================================================================
   SMART ATTENDANCE — Frontend Logic
   =================================================================
   Sidebar, toasts, class/sweep controls, status polling, feed toggle.
   All API endpoints unchanged from backend.
   ================================================================= */

/* -----------------------------------------------------------------
   Sidebar
   ----------------------------------------------------------------- */
function toggleSidebar() {
    const app = document.getElementById('app');
    app.classList.toggle('collapsed');
    localStorage.setItem('sidebar-collapsed', app.classList.contains('collapsed'));
}

function openMobileSidebar() {
    document.getElementById('sidebar').classList.add('mobile-open');
    document.getElementById('sidebar-backdrop').classList.add('visible');
}

function closeMobileSidebar() {
    document.getElementById('sidebar').classList.remove('mobile-open');
    document.getElementById('sidebar-backdrop').classList.remove('visible');
}

/* -----------------------------------------------------------------
   Toast Notifications
   ----------------------------------------------------------------- */
function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    if (!container) return;

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(function () {
        toast.classList.add('out');
        setTimeout(function () { toast.remove(); }, 250);
    }, 3000);
}

/* -----------------------------------------------------------------
   Class Controls
   ----------------------------------------------------------------- */
async function startClass() {
    try {
        await fetch('/api/start_class', { method: 'POST' });
        showToast('Class session started', 'success');
        refreshStatus();
    } catch (e) {
        showToast('Failed to start class', 'error');
    }
}

async function endClass() {
    if (!confirm('End the current class? Attendance will be finalized.')) return;
    try {
        await fetch('/api/end_class', { method: 'POST' });
        showToast('Class session ended', 'info');
        refreshStatus();
    } catch (e) {
        showToast('Failed to end class', 'error');
    }
}

async function forceSweep() {
    var btn = document.getElementById('btn-force-sweep');
    if (btn) btn.disabled = true;
    try {
        var res = await fetch('/api/force_sweep', { method: 'POST' });
        var data = await res.json();
        if (data.success) {
            showToast('AI Sweep triggered', 'success');
        } else {
            showToast(data.error || 'Cannot trigger sweep', 'error');
        }
        refreshStatus();
    } catch (e) {
        showToast('Failed to trigger sweep', 'error');
    }
    setTimeout(function () { if (btn) btn.disabled = false; }, 5000);
}

async function toggleDemoMode() {
    try {
        var res = await fetch('/api/toggle_demo_mode', { method: 'POST' });
        var data = await res.json();
        showToast(data.demo_mode ? 'Fast-track mode enabled' : 'Fast-track mode disabled', 'info');
        refreshStatus();
    } catch (e) {
        showToast('Failed to toggle demo mode', 'error');
    }
}

/* -----------------------------------------------------------------
   Live Feed Toggle
   ----------------------------------------------------------------- */
function toggleFeed() {
    var container = document.getElementById('feed-container');
    var btn = document.getElementById('toggle-feed');
    var img = document.getElementById('live-feed');
    var overlay = document.getElementById('feed-status');
    if (!container) return;

    if (container.style.display === 'none' || !container.style.display) {
        container.style.display = 'flex';
        if (btn) btn.textContent = 'Hide Feed';
        if (img && (!img.src || img.src.includes('#') || img.src === window.location.href)) {
            img.src = '/video_feed';
            if (overlay) overlay.style.display = 'none';
        }
    } else {
        container.style.display = 'none';
        if (btn) btn.textContent = 'Show Feed';
        if (img) img.src = '';
        if (overlay) overlay.style.display = 'block';
    }
}

/* -----------------------------------------------------------------
   Avatar Color Helper
   ----------------------------------------------------------------- */
function avatarColor(name) {
    var colors = ['#8b5cf6','#06b6d4','#f59e0b','#22c55e','#ef4444','#ec4899','#3b82f6','#14b8a6'];
    var hash = 0;
    for (var i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
}

/* -----------------------------------------------------------------
   Status Polling & UI Render
   ----------------------------------------------------------------- */
async function refreshStatus() {
    try {
        var res = await fetch('/api/status');
        if (!res.ok) return;
        var data = await res.json();

        /* Sidebar status */
        var navDot = document.getElementById('nav-status-dot');
        var navText = document.getElementById('nav-status-text');
        if (navDot) {
            navDot.className = data.camera_running
                ? 'status-dot status-dot--active'
                : 'status-dot status-dot--inactive';
        }
        if (navText) {
            navText.textContent = data.camera_running ? 'Online' : 'Offline';
        }

        /* Camera status (dashboard strip) */
        var camDot  = document.getElementById('status-camera-dot');
        var camText = document.getElementById('status-camera-text');
        if (camDot) {
            camDot.className = data.camera_running
                ? 'status-dot status-dot--active'
                : 'status-dot status-dot--inactive';
        }
        if (camText) {
            camText.textContent = data.camera_running ? 'Camera connected' : 'Camera disconnected';
        }

        /* Sweep status */
        var sweepDot  = document.getElementById('status-sweep-dot');
        var sweepText = document.getElementById('status-sweep-text');
        var sweepAlert = document.getElementById('sweep-alert');
        if (sweepDot) {
            if (data.sweep_in_progress) {
                sweepDot.className = 'status-dot status-dot--danger';
                if (sweepText) sweepText.textContent = 'Sweep active';
                if (sweepAlert) sweepAlert.style.display = 'block';
            } else {
                sweepDot.className = 'status-dot';
                if (sweepText) sweepText.textContent = 'Sweep idle';
                if (sweepAlert) sweepAlert.style.display = 'none';
            }
        }

        /* Session banner */
        var heading   = document.getElementById('class-status-heading');
        var meta      = document.getElementById('sweep-counter-text');
        var indicator = document.getElementById('session-indicator');
        var btnStart  = document.getElementById('btn-start-class');
        var btnEnd    = document.getElementById('btn-end-class');
        var btnForce  = document.getElementById('btn-force-sweep');
        var dlBtn     = document.getElementById('btn-download-csv');

        if (btnStart) {
            if (data.active_class) {
                if (heading)   heading.textContent = data.subject || 'Active Session';
                if (meta)      meta.textContent = data.total_sweeps + ' sweep' + (data.total_sweeps !== 1 ? 's' : '') + ' completed';
                if (indicator) indicator.className = 'session-indicator active';
                btnStart.style.display = 'none';
                btnEnd.style.display   = 'inline-flex';
                btnForce.style.display = 'inline-flex';
                if (dlBtn) {
                    dlBtn.href = '/download/' + data.class_id;
                    dlBtn.style.opacity = '1';
                    dlBtn.style.pointerEvents = 'auto';
                }
            } else {
                if (heading)   heading.textContent = 'No Active Class';
                if (meta)      meta.textContent = 'Start a session to begin attendance tracking.';
                if (indicator) indicator.className = 'session-indicator';
                btnStart.style.display = 'inline-flex';
                btnEnd.style.display   = 'none';
                btnForce.style.display = 'none';
                if (dlBtn) {
                    dlBtn.href = '#';
                    dlBtn.style.opacity = '0.5';
                    dlBtn.style.pointerEvents = 'none';
                }
            }
        }

        /* Stats */
        var statSweeps   = document.getElementById('stat-total-sweeps');
        var statStudents = document.getElementById('stat-students');
        if (statSweeps)   statSweeps.textContent   = data.total_sweeps || '0';
        if (statStudents) statStudents.textContent = data.summary ? data.summary.length : '0';

        /* Demo mode */
        var demoText = document.getElementById('demo-status-text');
        var demoBtn  = document.getElementById('btn-toggle-demo');
        if (demoText && demoBtn) {
            if (data.demo_mode) {
                demoText.textContent = 'ON';
                demoText.style.color = 'var(--amber)';
                demoBtn.textContent = 'Disable Fast-Track';
            } else {
                demoText.textContent = 'Off';
                demoText.style.color = '';
                demoBtn.textContent = 'Enable Fast-Track';
            }
        }

        /* Attendance table */
        var table    = document.getElementById('attendance-table');
        var tbody    = document.getElementById('attendance-tbody');
        var empty    = document.getElementById('empty-state');
        var emptyMsg = document.getElementById('empty-state-msg');

        if (table && tbody) {
            if (!data.active_class && (!data.summary || data.summary.length === 0)) {
                table.style.display = 'none';
                if (empty) empty.style.display = 'flex';
                if (emptyMsg) emptyMsg.textContent = 'No active class session.';
            } else if (data.active_class && (!data.summary || data.summary.length === 0)) {
                table.style.display = 'none';
                if (empty) empty.style.display = 'flex';
                if (emptyMsg) emptyMsg.textContent = 'Waiting for first sweep...';
            } else if (data.summary && data.summary.length > 0) {
                if (empty) empty.style.display = 'none';
                table.style.display = 'table';

                var html = '';
                data.summary.forEach(function (r, i) {
                    var level = r.percentage >= 80 ? 'high' : (r.percentage >= 50 ? 'medium' : 'low');
                    var initial = r.name.charAt(0).toUpperCase();
                    var color = avatarColor(r.name);

                    html += '<tr>'
                        + '<td>' + (i + 1) + '</td>'
                        + '<td><div class="flex-center gap-sm">'
                        +   '<span class="avatar" style="background:' + color + '">' + initial + '</span>'
                        +   '<strong>' + r.name + '</strong>'
                        + '</div></td>'
                        + '<td><code>' + r.user_id + '</code></td>'
                        + '<td>' + r.sweeps_attended + ' / ' + r.total_sweeps + '</td>'
                        + '<td><div class="progress-cell">'
                        +   '<div class="progress-inline">'
                        +     '<div class="progress-fill ' + level + '" style="width:' + r.percentage + '%"></div>'
                        +   '</div>'
                        +   '<span class="progress-text ' + level + '">' + r.percentage + '%</span>'
                        + '</div></td>'
                        + '</tr>';
                });
                tbody.innerHTML = html;
            }
        }

    } catch (e) {
        /* Silent fail on network disconnect */
    }
}

/* -----------------------------------------------------------------
   Lightweight sidebar status poll (runs on all pages)
   ----------------------------------------------------------------- */
async function pollSidebarStatus() {
    try {
        var res = await fetch('/api/status');
        if (!res.ok) return;
        var data = await res.json();
        var dot  = document.getElementById('nav-status-dot');
        var text = document.getElementById('nav-status-text');
        if (dot) {
            dot.className = data.camera_running
                ? 'status-dot status-dot--active'
                : 'status-dot status-dot--inactive';
        }
        if (text) {
            text.textContent = data.camera_running ? 'Online' : 'Offline';
        }
    } catch (e) { /* silent */ }
}

/* -----------------------------------------------------------------
   Initialise
   ----------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', function () {
    /* Restore sidebar state */
    if (localStorage.getItem('sidebar-collapsed') === 'true') {
        var app = document.getElementById('app');
        if (app) app.classList.add('collapsed');
    }

    /* Poll sidebar status on all pages (slower interval) */
    if (document.getElementById('nav-status-dot')) {
        pollSidebarStatus();
        setInterval(pollSidebarStatus, 5000);
    }
});

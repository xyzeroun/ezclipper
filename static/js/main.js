/**
 * TikTok Clipper — Frontend Logic
 */

// ========================
// Tab Navigation
// ========================
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        switchTab(tab);
    });
});

function switchTab(tab) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');

    // Load data for specific tabs
    if (tab === 'clips') loadAllClips();
    if (tab === 'schedule') loadJobs();
    if (tab === 'settings') loadSettings();
}

// ========================
// Toast Notifications
// ========================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ========================
// Process Video
// ========================
const btnProcess = document.getElementById('btn-process');
const inputUrl = document.getElementById('input-url');
const inputClips = document.getElementById('input-clips');
const inputType = document.getElementById('input-type');
const inputLivestreamDuration = document.getElementById('input-livestream-duration');

// Show/hide livestream option
inputType.addEventListener('change', () => {
    const show = inputType.value === 'livestream';
    document.querySelector('.livestream-option').style.display = show ? 'block' : 'none';
});

btnProcess.addEventListener('click', async () => {
    const url = inputUrl.value.trim();
    if (!url) {
        showToast('Please enter a YouTube URL', 'error');
        return;
    }

    btnProcess.disabled = true;
    btnProcess.innerHTML = '<span class="btn-icon">⏳</span> Processing...';

    try {
        const resp = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                max_clips: parseInt(inputClips.value),
                is_livestream: inputType.value === 'livestream',
                livestream_duration: parseInt(inputLivestreamDuration.value),
            }),
        });

        const data = await resp.json();
        if (data.error) {
            showToast(data.error, 'error');
            resetProcessButton();
            return;
        }

        // Show progress
        showProgress();
        pollStatus(data.job_id);

    } catch (err) {
        showToast('Connection error: ' + err.message, 'error');
        resetProcessButton();
    }
});

function resetProcessButton() {
    btnProcess.disabled = false;
    btnProcess.innerHTML = '<span class="btn-icon">✨</span> Generate Clips';
}

// ========================
// Progress Tracking
// ========================
let pollInterval = null;

function showProgress() {
    document.getElementById('progress-card').style.display = 'block';
    document.getElementById('results-card').style.display = 'none';
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-percent').textContent = '0%';
    document.getElementById('progress-step').textContent = 'Starting...';
    document.getElementById('log-content').innerHTML = '';
}

function pollStatus(jobId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/status/${jobId}`);
            const data = await resp.json();

            // Update progress
            document.getElementById('progress-bar').style.width = `${data.progress}%`;
            document.getElementById('progress-percent').textContent = `${data.progress}%`;
            document.getElementById('progress-step').textContent = data.current_step || '';

            // Update log
            if (data.log && data.log.length > 0) {
                const logHtml = data.log.map(l => `<div class="log-line">${escapeHtml(l)}</div>`).join('');
                document.getElementById('log-content').innerHTML = logHtml;
                const logContainer = document.getElementById('log-container');
                logContainer.scrollTop = logContainer.scrollHeight;
            }

            // Check completion
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                pollInterval = null;
                showToast('🎉 Clips generated successfully!', 'success');
                showResults(data.clips);
                resetProcessButton();
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                pollInterval = null;
                showToast('❌ Error: ' + (data.error || 'Unknown error'), 'error');
                resetProcessButton();
            }

        } catch (err) {
            console.error('Poll error:', err);
        }
    }, 1500);
}

// ========================
// Results Display
// ========================
function showResults(clips) {
    const card = document.getElementById('results-card');
    const grid = document.getElementById('clips-grid');
    card.style.display = 'block';

    if (!clips || clips.length === 0) {
        grid.innerHTML = '<p class="empty-state">No clips were generated.</p>';
        return;
    }

    grid.innerHTML = clips.map(clip => `
        <div class="clip-card">
            <div class="clip-preview">
                <video controls preload="metadata">
                    <source src="${clip.url}" type="video/mp4">
                </video>
            </div>
            <div class="clip-info">
                <div class="clip-title" title="${escapeHtml(clip.title)}">${escapeHtml(clip.title)}</div>
                <div class="clip-meta">
                    <span>⏱️ ${clip.duration}s</span>
                    <span>📍 ${formatTime(clip.start)} - ${formatTime(clip.end)}</span>
                </div>
                ${clip.reason ? `<div class="clip-meta" style="margin-bottom:12px">${escapeHtml(clip.reason)}</div>` : ''}
                <div class="clip-actions">
                    <a href="${clip.url}" download class="btn btn-sm">
                        ⬇️ Download
                    </a>
                    <button class="btn btn-sm btn-danger" onclick="deleteClip('${clip.filename}', this)">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// ========================
// All Clips
// ========================
async function loadAllClips() {
    try {
        const resp = await fetch('/api/clips');
        const data = await resp.json();
        const list = document.getElementById('all-clips-list');

        if (!data.clips || data.clips.length === 0) {
            list.innerHTML = '<p class="empty-state">No clips yet. Generate some from the Home tab!</p>';
            return;
        }

        list.innerHTML = data.clips.map(clip => `
            <div class="clip-list-item">
                <div class="clip-list-info">
                    <span class="clip-list-icon">🎬</span>
                    <div>
                        <div class="clip-list-name">${escapeHtml(clip.filename)}</div>
                        <div class="clip-list-size">${clip.size_mb} MB</div>
                    </div>
                </div>
                <div class="clip-list-actions">
                    <a href="${clip.url}" download class="btn btn-sm">⬇️</a>
                    <button class="btn btn-sm btn-danger" onclick="deleteClip('${clip.filename}', this)">🗑️</button>
                </div>
            </div>
        `).join('');

    } catch (err) {
        showToast('Failed to load clips', 'error');
    }
}

document.getElementById('btn-refresh-clips').addEventListener('click', loadAllClips);

async function deleteClip(filename, btn) {
    if (!confirm(`Delete ${filename}?`)) return;
    try {
        await fetch(`/api/clips/${filename}`, { method: 'DELETE' });
        btn.closest('.clip-card, .clip-list-item').remove();
        showToast('Clip deleted', 'info');
    } catch (err) {
        showToast('Failed to delete', 'error');
    }
}

// ========================
// Scheduling
// ========================
document.getElementById('btn-schedule').addEventListener('click', async () => {
    const url = document.getElementById('schedule-url').value.trim();
    if (!url) {
        showToast('Please enter a URL', 'error');
        return;
    }

    const scheduleTime = document.getElementById('schedule-time').value;
    const maxClips = parseInt(document.getElementById('schedule-clips').value);

    try {
        const resp = await fetch('/api/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                schedule_time: scheduleTime || null,
                max_clips: maxClips,
            }),
        });
        const data = await resp.json();
        showToast(scheduleTime ? 'Job scheduled!' : 'Processing started!', 'success');
        loadJobs();
        document.getElementById('schedule-url').value = '';
    } catch (err) {
        showToast('Failed to schedule: ' + err.message, 'error');
    }
});

async function loadJobs() {
    try {
        const resp = await fetch('/api/jobs');
        const data = await resp.json();
        const list = document.getElementById('jobs-list');

        if (!data.jobs || data.jobs.length === 0) {
            list.innerHTML = '<p class="empty-state">No scheduled jobs.</p>';
            return;
        }

        list.innerHTML = data.jobs.map(job => `
            <div class="job-item">
                <div class="job-info">
                    <div class="job-url" title="${escapeHtml(job.url)}">${escapeHtml(job.url)}</div>
                    <div class="job-schedule">
                        ${job.schedule_time ? '📅 ' + new Date(job.schedule_time).toLocaleString() : '⚡ Immediate'}
                        | Clips: ${job.max_clips}
                    </div>
                </div>
                <span class="job-status ${job.status}">${job.status}</span>
                <button class="btn btn-sm btn-danger" onclick="deleteJob('${job.id}', this)">🗑️</button>
            </div>
        `).join('');

    } catch (err) {
        showToast('Failed to load jobs', 'error');
    }
}

async function deleteJob(jobId, btn) {
    try {
        await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
        btn.closest('.job-item').remove();
        showToast('Job deleted', 'info');
    } catch (err) {
        showToast('Failed to delete job', 'error');
    }
}

// ========================
// Settings
// ========================
async function loadSettings() {
    try {
        const resp = await fetch('/api/settings');
        const s = await resp.json();

        // We don't pre-fill API keys for security (they're masked)
        document.getElementById('set-openrouter-model').value = s.openrouter_model || 'openai/gpt-4o-mini';
        document.getElementById('set-whisper-model').value = s.whisper_model || 'base';
        document.getElementById('set-whisper-lang').value = s.whisper_language || 'id';
        document.getElementById('set-min-duration').value = s.min_clip_duration || 15;
        document.getElementById('set-max-duration').value = s.max_clip_duration || 60;
        document.getElementById('set-font-size').value = s.caption_font_size || 20;
        document.getElementById('set-caption-pos').value = s.caption_position || 'bottom';
        document.getElementById('set-caption-color').value = s.caption_color || '#FFFFFF';
        document.getElementById('set-highlight-color').value = s.caption_highlight_color || '#FFD700';
        document.getElementById('set-cookies-browser').value = s.youtube_cookies_browser || 'chrome';

    } catch (err) {
        console.error('Failed to load settings:', err);
    }
}

document.getElementById('btn-save-settings').addEventListener('click', async () => {
    const settings = {};

    // API Keys — only send if user typed something
    const orKey = document.getElementById('set-openrouter-key').value.trim();
    if (orKey) settings.openrouter_api_key = orKey;

    const kieKey = document.getElementById('set-kie-key').value.trim();
    if (kieKey) settings.kie_api_key = kieKey;

    settings.openrouter_model = document.getElementById('set-openrouter-model').value;
    settings.whisper_model = document.getElementById('set-whisper-model').value;
    settings.whisper_language = document.getElementById('set-whisper-lang').value;
    settings.min_clip_duration = parseInt(document.getElementById('set-min-duration').value);
    settings.max_clip_duration = parseInt(document.getElementById('set-max-duration').value);
    settings.caption_font_size = parseInt(document.getElementById('set-font-size').value);
    settings.caption_position = document.getElementById('set-caption-pos').value;
    settings.caption_color = document.getElementById('set-caption-color').value;
    settings.caption_highlight_color = document.getElementById('set-highlight-color').value;
    settings.youtube_cookies_browser = document.getElementById('set-cookies-browser').value;

    try {
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });

        const status = document.getElementById('save-status');
        status.textContent = '✅ Saved!';
        status.classList.add('visible');
        setTimeout(() => status.classList.remove('visible'), 2000);

        showToast('Settings saved!', 'success');
    } catch (err) {
        showToast('Failed to save settings', 'error');
    }
});

// ========================
// Utilities
// ========================
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// ========================
// Keyboard shortcuts
// ========================
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
        if (document.getElementById('tab-home').classList.contains('active')) {
            btnProcess.click();
        }
    }
});

// ========================
// Init
// ========================
loadSettings();

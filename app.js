// Application State
let applications = JSON.parse(localStorage.getItem('applications')) || [];
let userProfile = JSON.parse(localStorage.getItem('userProfile')) || {};
let currentFilter = 'all';

// Tab Navigation
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(target).classList.add('active');
        
        if (target === 'dashboard') renderDashboard();
    });
});

// Application Form Submission
const appForm = document.getElementById('applicationForm');
if (appForm) {
    appForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const newApp = {
            id: Date.now().toString(),
            appliedOn: document.getElementById('appliedOn').value,
            platform: document.getElementById('platform').value,
            company: document.getElementById('company').value,
            role: document.getElementById('role').value,
            status: document.getElementById('status').value,
            notes: document.getElementById('notes').value
        };
        
        applications.push(newApp);
        localStorage.setItem('applications', JSON.stringify(applications));
        
        appForm.reset();
        renderApplications();
        alert('Application added successfully!');
    });
}

// Profile Form Submission
const profileForm = document.getElementById('profileForm');
if (profileForm) {
    profileForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        userProfile = {
            name: document.getElementById('name').value,
            currentRole: document.getElementById('currentRole').value,
            skills: document.getElementById('skills').value,
            achievements: document.getElementById('achievements').value
        };
        
        localStorage.setItem('userProfile', JSON.stringify(userProfile));
        alert('Profile saved successfully!');
    });
}

// Load Profile on Page Load
window.addEventListener('DOMContentLoaded', () => {
    if (userProfile.name) {
        document.getElementById('name').value = userProfile.name || '';
        document.getElementById('currentRole').value = userProfile.currentRole || '';
        document.getElementById('skills').value = userProfile.skills || '';
        document.getElementById('achievements').value = userProfile.achievements || '';
    }
    
    renderApplications();
    renderDashboard();
});

// Render Applications Table
function renderApplications() {
    const body = document.getElementById('applicationTableBody');
    if (!body) return;
    
    const filtered = currentFilter === 'all' 
        ? applications 
        : applications.filter(app => app.status === currentFilter);
    
    if (filtered.length === 0) {
        body.innerHTML = '<tr><td colspan="6" style="text-align:center;">No applications found</td></tr>';
        return;
    }
    
    body.innerHTML = filtered.map(app => `
        <tr>
            <td>${app.appliedOn}</td>
            <td>${app.platform}</td>
            <td>${app.company}</td>
            <td>${app.role}</td>
            <td><span class="status ${getStatusClass(app.status)}">${app.status}</span></td>
            <td><button onclick="removeApplication('${app.id}')">Delete</button></td>
        </tr>
    `).join('');
}

// Remove Application
window.removeApplication = function(id) {
    if (confirm('Delete this application?')) {
        applications = applications.filter(app => app.id !== id);
        localStorage.setItem('applications', JSON.stringify(applications));
        renderApplications();
        renderDashboard();
    }
};

// Filter Applications
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        currentFilter = btn.dataset.filter;
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderApplications();
    });
});

// Render Dashboard
function renderDashboard() {
    document.getElementById('totalApps').textContent = applications.length;
    
    const statusCounts = applications.reduce((acc, app) => {
        acc[app.status] = (acc[app.status] || 0) + 1;
        return acc;
    }, {});
    
    document.getElementById('offersReceived').textContent = statusCounts['Offer'] || 0;
    
    const interviewCount = statusCounts['Interview'] || 0;
    const responseRate = applications.length > 0 
        ? Math.round((interviewCount / applications.length) * 100) 
        : 0;
    document.getElementById('responseRate').textContent = responseRate + '%';
    
    // Pipeline Bars
    const pipeline = document.getElementById('pipelineBars');
    if (pipeline) {
        const stages = ['Applied', 'Under Review', 'Screening', 'Interview', 'Offer'];
        pipeline.innerHTML = stages.map(stage => {
            const count = statusCounts[stage] || 0;
            return `
                <div class="pipe-stage">
                    <div class="pipe-label">${stage}</div>
                    <div class="pipe-bar">
                        <div class="pipe-fill" style="width: ${count * 20}%"></div>
                    </div>
                    <div class="pipe-count">${count}</div>
                </div>
            `;
        }).join('');
    }
    
    // Recent Applications
    const recentBody = document.getElementById('recentTableBody');
    if (recentBody) {
        const recent = applications.slice(-5).reverse();
        recentBody.innerHTML = recent.map(app => `
            <tr>
                <td>${app.appliedOn}</td>
                <td>${app.platform}</td>
                <td>${app.company}</td>
                <td>${app.role}</td>
                <td><span class="status ${getStatusClass(app.status)}">${app.status}</span></td>
            </tr>
        `).join('');
    }
}

// Status Class Helper
function getStatusClass(status) {
    const statusMap = {
        'Applied': 'status-applied',
        'Under Review': 'status-review',
        'Screening': 'status-screening',
        'Interview': 'status-interview',
        'Offer': 'status-offer',
        'Rejected': 'status-rejected'
    };
    return statusMap[status] || '';
}

// AI Generator Functions
document.getElementById('generateCoverBtn')?.addEventListener('click', () => {
    const jd = document.getElementById('jobDescription').value;
    const cv = document.getElementById('companyValues').value;
    
    if (!jd) {
        alert('Please enter a job description');
        return;
    }
    
    const output = generateCoverLetter(jd, cv);
    showOutput(output);
});

document.getElementById('generateResumeBtn')?.addEventListener('click', () => {
    const jd = document.getElementById('jobDescription').value;
    
    if (!jd) {
        alert('Please enter a job description');
        return;
    }
    
    const output = generateResumeSummary(jd);
    showOutput(output);
});

function generateCoverLetter(jd, cv) {
    return `Dear Hiring Manager,

I am writing to express my strong interest in the position at your organization. With my background as a ${userProfile.currentRole || '[Your Role]'} and expertise in ${userProfile.skills || '[Your Skills]'}, I am confident I can contribute significantly to your team.

${userProfile.achievements ? 'Key achievements include: ' + userProfile.achievements : ''}

I am particularly excited about this opportunity because it aligns perfectly with my career goals and expertise. I look forward to discussing how my skills can benefit your organization.

Best regards,
${userProfile.name || '[Your Name]'}`;
}

function generateResumeSummary(jd) {
    return `PROFESSIONAL SUMMARY

${userProfile.currentRole || '[Your Current Role]'} with proven expertise in ${userProfile.skills || '[Your Skills]'}. 

KEY SKILLS:
${userProfile.skills?.split(',').map(s => `• ${s.trim()}`).join('\n') || '• [Add your skills]'}

ACHIEVEMENTS:
${userProfile.achievements?.split(',').map(a => `• ${a.trim()}`).join('\n') || '• [Add your achievements]'}`;
}

function showOutput(text) {
    const outputPanel = document.getElementById('generatedOutput');
    const outputText = document.getElementById('outputText');
    
    if (outputPanel && outputText) {
        outputText.textContent = text;
        outputPanel.style.display = 'block';
    }
}

document.getElementById('copyOutputBtn')?.addEventListener('click', () => {
    const outputText = document.getElementById('outputText').textContent;
    navigator.clipboard.writeText(outputText).then(() => {
        alert('Copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy. Please copy manually.');
    });
});

// Export Data Functions
document.getElementById('exportDataBtn')?.addEventListener('click', () => {
    const dataStr = JSON.stringify({
        applications: applications,
        userProfile: userProfile,
        exportDate: new Date().toISOString()
    }, null, 2);
    
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `job-tracker-backup-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
});

// Import Data Functions
document.getElementById('importDataBtn')?.addEventListener('click', () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const data = JSON.parse(event.target.result);
                
                if (data.applications) {
                    applications = data.applications;
                    localStorage.setItem('applications', JSON.stringify(applications));
                }
                
                if (data.userProfile) {
                    userProfile = data.userProfile;
                    localStorage.setItem('userProfile', JSON.stringify(userProfile));
                }
                
                renderApplications();
                renderDashboard();
                alert('Data imported successfully!');
                location.reload();
            } catch (err) {
                console.error('Import error:', err);
                alert('Failed to import data. Please check the file format.');
            }
        };
        reader.readAsText(file);
    };
    
    input.click();
});

// Clear All Data
document.getElementById('clearDataBtn')?.addEventListener('click', () => {
    if (confirm('Are you sure you want to delete ALL data? This cannot be undone!')) {
        if (confirm('Really delete everything? Last chance!')) {
            localStorage.clear();
            applications = [];
            userProfile = {};
            renderApplications();
            renderDashboard();
            alert('All data cleared!');
            location.reload();
        }
    }
});

// Initialize on load
console.log('Job Application Tracker loaded successfully!');
console.log(`Total applications: ${applications.length}`);

// ==========================================================================
// ATS Optimizer
// ==========================================================================

// Sub-navigation
document.querySelectorAll('.ats-nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.ats-nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.ats-panel').forEach(p => p.style.display = 'none');
        btn.classList.add('active');
        const panel = document.getElementById('ats-' + btn.dataset.ats);
        if (panel) panel.style.display = 'block';
    });
});

function atsBackend() {
    const url = (document.getElementById('atsBackendUrl')?.value || '').trim();
    return url || 'http://localhost:5001';
}

async function atsPost(endpoint, body) {
    const base = atsBackend();
    const resp = await fetch(`${base}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return resp.json();
}

function atsLoading(outputId) {
    const el = document.getElementById(outputId);
    el.style.display = 'block';
    el.innerHTML = '<div class="ats-spinner">Analyzing with Claude AI...</div>';
    return el;
}

function atsError(outputId, message) {
    const el = document.getElementById(outputId);
    el.style.display = 'block';
    el.innerHTML = `<div class="ats-error">Error: ${message}</div>`;
}

function atsRenderJson(outputId, data, title) {
    const el = document.getElementById(outputId);
    el.style.display = 'block';
    el.innerHTML = `
        <div class="ats-result-header">
            <strong>${title}</strong>
            <button class="ats-copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('${outputId}-text').innerText)">Copy</button>
        </div>
        <div id="${outputId}-text" class="ats-result-body">${atsFormatResult(data)}</div>`;
}

function atsRenderText(outputId, text, title) {
    const el = document.getElementById(outputId);
    el.style.display = 'block';
    el.innerHTML = `
        <div class="ats-result-header">
            <strong>${title}</strong>
            <button class="ats-copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('${outputId}-text').innerText)">Copy</button>
        </div>
        <pre id="${outputId}-text" class="ats-result-body ats-pre">${escapeHtml(text)}</pre>`;
}

function escapeHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function atsFormatResult(obj, indent = 0) {
    if (typeof obj === 'string') return `<span>${escapeHtml(obj)}</span>`;
    if (Array.isArray(obj)) {
        return '<ul>' + obj.map(item => `<li>${atsFormatResult(item, indent + 1)}</li>`).join('') + '</ul>';
    }
    if (typeof obj === 'object' && obj !== null) {
        return Object.entries(obj).map(([k, v]) => {
            const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            if (k === 'score') {
                const color = v >= 70 ? '#4caf50' : v >= 50 ? '#ff9800' : '#f44336';
                return `<div class="ats-field"><span class="ats-label">${escapeHtml(label)}</span><span class="ats-score" style="color:${color};font-size:2em;font-weight:700">${v}/100</span></div>`;
            }
            return `<div class="ats-field"><span class="ats-label">${escapeHtml(label)}</span><div class="ats-value">${atsFormatResult(v, indent + 1)}</div></div>`;
        }).join('');
    }
    return `<span>${escapeHtml(String(obj))}</span>`;
}

// Check provider button
document.getElementById('btnCheckProvider')?.addEventListener('click', async () => {
    const base = atsBackend();
    const statusEl = document.getElementById('atsProviderStatus');
    statusEl.style.display = 'block';
    statusEl.textContent = 'Checking...';
    statusEl.style.background = '#1a2a50';
    statusEl.style.color = '#aaa';
    try {
        const res = await fetch(`${base}/api/ats/provider`);
        const data = await res.json();
        if (data.configured) {
            const icons = { anthropic: '🟣', openai: '🟢', groq: '🔵' };
            statusEl.textContent = `${icons[data.provider] || '✅'} Connected — using ${data.provider.toUpperCase()} (${data.model})`;
            statusEl.style.background = '#0f2e1a';
            statusEl.style.color = '#5de0a0';
        } else {
            statusEl.textContent = '⚠️ No API key found on backend. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY.';
            statusEl.style.background = '#2a1a0a';
            statusEl.style.color = '#ffb347';
        }
    } catch {
        statusEl.textContent = `❌ Cannot reach backend at ${base}. Is it running?`;
        statusEl.style.background = '#2a0d0d';
        statusEl.style.color = '#ff6b6b';
    }
});

// Button handlers

document.getElementById('btnParseJd')?.addEventListener('click', async () => {
    const jd = document.getElementById('atsJd').value.trim();
    if (!jd) return alert('Paste a job description first.');
    atsLoading('parseJdOutput');
    const res = await atsPost('/api/ats/parse-jd', { jd_text: jd });
    if (res.ok) atsRenderJson('parseJdOutput', res.result, 'Job Description Analysis');
    else atsError('parseJdOutput', res.error);
});

document.getElementById('btnScore')?.addEventListener('click', async () => {
    const jd = document.getElementById('atsJd').value.trim();
    const resume = document.getElementById('atsResume').value.trim();
    if (!jd || !resume) return alert('Paste both your resume and the job description.');
    atsLoading('scoreOutput');
    const res = await atsPost('/api/ats/score', { resume_text: resume, jd_text: jd });
    if (res.ok) atsRenderJson('scoreOutput', res.result, 'Alignment Score Report');
    else atsError('scoreOutput', res.error);
});

document.getElementById('btnRewriteBullets')?.addEventListener('click', async () => {
    const jd = document.getElementById('atsJd').value.trim();
    const rawBullets = document.getElementById('atsBullets').value.trim();
    const context = document.getElementById('atsBulletContext').value.trim();
    if (!jd || !rawBullets) return alert('Paste the job description and your bullet points.');
    const bullets = rawBullets.split('\n').map(b => b.replace(/^[-•*]\s*/, '').trim()).filter(Boolean);
    atsLoading('bulletsOutput');
    const res = await atsPost('/api/ats/rewrite-bullets', {
        bullets,
        jd_context: jd,
        candidate_context: context,
    });
    if (res.ok) atsRenderJson('bulletsOutput', { rewritten_bullets: res.result }, 'Rewritten Bullet Points');
    else atsError('bulletsOutput', res.error);
});

document.getElementById('btnCoverLetter')?.addEventListener('click', async () => {
    const jd = document.getElementById('atsJd').value.trim();
    const resume = document.getElementById('atsResume').value.trim();
    const company = document.getElementById('atsCoverCompany').value.trim();
    const role = document.getElementById('atsCoverRole').value.trim();
    const name = document.getElementById('atsCoverName').value.trim();
    const manager = document.getElementById('atsCoverManager').value.trim();
    if (!jd || !resume || !company || !role) return alert('Fill in the JD, resume, company, and role fields.');
    atsLoading('coverOutput');
    const res = await atsPost('/api/ats/cover-letter', {
        resume_text: resume,
        jd_text: jd,
        company_name: company,
        role_title: role,
        candidate_name: name,
        hiring_manager: manager,
    });
    if (res.ok) atsRenderText('coverOutput', res.result, 'Cover Letter');
    else atsError('coverOutput', res.error);
});

document.getElementById('btnLinkedIn')?.addEventListener('click', async () => {
    const resume = document.getElementById('atsResume').value.trim();
    const role = document.getElementById('atsLinkedInRole').value.trim();
    const industry = document.getElementById('atsLinkedInIndustry').value.trim();
    if (!resume || !role) return alert('Paste your resume and enter the target role.');
    atsLoading('linkedinOutput');
    const res = await atsPost('/api/ats/linkedin', {
        profile_data: { raw_resume: resume },
        target_role: role,
        target_industry: industry,
    });
    if (res.ok) atsRenderJson('linkedinOutput', res.result, 'LinkedIn Optimization');
    else atsError('linkedinOutput', res.error);
});

document.getElementById('btnFullResume')?.addEventListener('click', async () => {
    const jd = document.getElementById('atsJd').value.trim();
    const resume = document.getElementById('atsResume').value.trim();
    const role = document.getElementById('atsFullRole').value.trim();
    const company = document.getElementById('atsFullCompany').value.trim();
    if (!jd || !resume || !role) return alert('Paste your resume, the JD, and the target role.');
    atsLoading('fullResumeOutput');
    const res = await atsPost('/api/ats/resume', {
        resume_data: { raw_resume: resume },
        jd_text: jd,
        target_role: role,
        target_company: company,
    });
    if (res.ok) atsRenderText('fullResumeOutput', res.result, 'ATS-Optimized Resume');
    else atsError('fullResumeOutput', res.error);
});
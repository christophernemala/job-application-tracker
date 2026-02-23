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
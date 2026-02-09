const STORAGE_KEY = 'aiJobAgentDataV1';
const state = {
  applications: [],
  profile: {}
};

function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return;
  try {
    const parsed = JSON.parse(saved);
    state.applications = parsed.applications || [];
    state.profile = parsed.profile || {};
  } catch {
    state.applications = [];
    state.profile = {};
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function switchTab(tabId) {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.tab === tabId);
  });
  document.querySelectorAll('.panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === tabId);
  });
}

function statusClass(status) {
  return status.toLowerCase().replaceAll(' ', '-');
}

function renderApplications() {
  const body = document.getElementById('applicationTableBody');
  const search = document.getElementById('searchInput').value.toLowerCase();
  const platformFilter = document.getElementById('platformFilter').value;
  const statusFilter = document.getElementById('statusFilter').value;

  const rows = state.applications.filter(app => {
    const haystack = `${app.company} ${app.role} ${app.location || ''}`.toLowerCase();
    const matchesSearch = haystack.includes(search);
    const matchesPlatform = platformFilter === 'all' || app.platform === platformFilter;
    const matchesStatus = statusFilter === 'all' || app.status === statusFilter;
    return matchesSearch && matchesPlatform && matchesStatus;
  });

  body.innerHTML = rows.map(app => `
    <tr>
      <td>${app.appliedOn}</td>
      <td>${app.platform}</td>
      <td>${app.company}</td>
      <td>${app.role}</td>
      <td><span class="badge ${statusClass(app.status)}">${app.status}</span></td>
      <td><button class="btn secondary" onclick="removeApplication('${app.id}')">Delete</button></td>
    </tr>
  `).join('');
}

function renderDashboard() {
  const total = state.applications.length;
  const interview = state.applications.filter(a => a.status === 'Interview').length;
  const offer = state.applications.filter(a => a.status === 'Offer').length;
  const responded = state.applications.filter(a => ['Under Review', 'Interview', 'Offer'].includes(a.status)).length;
  const responseRate = total ? Math.round((responded / total) * 100) : 0;

  document.getElementById('totalApplications').textContent = total;
  document.getElementById('interviewCount').textContent = interview;
  document.getElementById('offerCount').textContent = offer;
  document.getElementById('responseRate').textContent = `${responseRate}%`;

  const pipelineStatuses = ['Applied', 'Under Review', 'Interview', 'Offer', 'Rejected'];
  const pipelineHtml = pipelineStatuses.map(status => {
    const count = state.applications.filter(a => a.status === status).length;
    const width = total ? (count / total) * 100 : 0;
    return `<div class="pipeline-row"><strong>${status}</strong><div class="bar-wrap"><div class="bar" style="width:${width}%"></div></div><span>${count}</span></div>`;
  }).join('');
  document.getElementById('pipelineBars').innerHTML = pipelineHtml;

  const recent = [...state.applications]
    .sort((a, b) => new Date(b.appliedOn) - new Date(a.appliedOn))
    .slice(0, 5);

  document.getElementById('recentTableBody').innerHTML = recent.map(app => `
    <tr><td>${app.appliedOn}</td><td>${app.platform}</td><td>${app.company}</td><td>${app.role}</td><td>${app.status}</td></tr>
  `).join('');
}

function fillProfileForm() {
  const fields = ['fullName', 'email', 'phone', 'experience', 'skills', 'achievements'];
  fields.forEach(key => {
    if (state.profile[key]) document.getElementById(key).value = state.profile[key];
  });
}

function removeApplication(id) {
  state.applications = state.applications.filter(app => app.id !== id);
  saveState();
  renderApplications();
  renderDashboard();
}
window.removeApplication = removeApplication;

function generateCoverLetter() {
  const profile = state.profile;
  const company = document.getElementById('targetCompany').value || 'Hiring Team';
  const role = document.getElementById('targetRole').value || 'the role';
  const jobDescription = document.getElementById('jobDescription').value;
  const companyValues = document.getElementById('companyValues').value;

  return `Dear ${company} Recruitment Team,\n\nI am excited to apply for ${role}. With ${profile.experience || 'several'} years of experience, I have delivered measurable outcomes in ${profile.skills || 'core business functions'}.\n\nMy relevant achievements include:\n${profile.achievements || '- Led high-impact initiatives across teams.'}\n\nI am particularly drawn to your team because: ${companyValues || 'your commitment to innovation and execution excellence'}.\n\nBased on the job requirements, I can contribute immediately in:\n${jobDescription || '- Stakeholder collaboration\n- Data-driven execution\n- Process optimization'}\n\nThank you for considering my application.\n\nSincerely,\n${profile.fullName || 'Candidate'}`;
}

function generateTailoredResumeSummary() {
  const profile = state.profile;
  const role = document.getElementById('targetRole').value || 'target role';
  const description = document.getElementById('jobDescription').value;
  const skills = (profile.skills || '').split(',').map(s => s.trim()).filter(Boolean);

  return `Professional Summary\n${profile.fullName || 'Candidate'} is a results-focused professional with ${profile.experience || 'multiple'} years of experience, targeting ${role}.\n\nCore Skills\n${skills.length ? skills.map(s => `• ${s}`).join('\n') : '• Cross-functional collaboration\n• Project execution\n• Analytical problem solving'}\n\nTailored Positioning\n${description || 'Align experience with the role by emphasizing customer impact, measurable achievements, and ownership.'}\n\nHighlighted Achievement\n${profile.achievements || 'Drove continuous improvement initiatives that improved performance metrics and stakeholder satisfaction.'}`;
}

function bindEvents() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  document.getElementById('applicationForm').addEventListener('submit', event => {
    event.preventDefault();
    const app = {
      id: crypto.randomUUID(),
      platform: document.getElementById('platform').value,
      company: document.getElementById('company').value,
      role: document.getElementById('role').value,
      location: document.getElementById('location').value,
      jobUrl: document.getElementById('jobUrl').value,
      status: document.getElementById('status').value,
      notes: document.getElementById('notes').value,
      appliedOn: new Date().toISOString().slice(0, 10)
    };
    state.applications.unshift(app);
    saveState();
    event.target.reset();
    renderApplications();
    renderDashboard();
  });

  ['searchInput', 'platformFilter', 'statusFilter'].forEach(id => {
    document.getElementById(id).addEventListener('input', renderApplications);
    document.getElementById(id).addEventListener('change', renderApplications);
  });

  document.getElementById('profileForm').addEventListener('submit', event => {
    event.preventDefault();
    const fields = ['fullName', 'email', 'phone', 'experience', 'skills', 'achievements'];
    fields.forEach(field => {
      state.profile[field] = document.getElementById(field).value;
    });
    saveState();
  });

  document.getElementById('generateCoverBtn').addEventListener('click', () => {
    document.getElementById('generatedOutput').value = generateCoverLetter();
  });

  document.getElementById('generateResumeBtn').addEventListener('click', () => {
    document.getElementById('generatedOutput').value = generateTailoredResumeSummary();
  });

  document.getElementById('copyOutputBtn').addEventListener('click', async () => {
    const text = document.getElementById('generatedOutput').value;
    if (!text) return;
    await navigator.clipboard.writeText(text);
  });
}

function init() {
  loadState();
  bindEvents();
  fillProfileForm();
  renderApplications();
  renderDashboard();
}

init();

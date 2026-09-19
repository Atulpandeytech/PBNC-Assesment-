import { api } from './api.js';

// Application State
const state = {
  currentTab: 'dashboard',
  documents: [],
  selectedDocId: null,
  questions: [],
  selectedQuestionId: null,
  activeFilterStatus: '',
  pollingInterval: null,
};

// DOM Utility
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// Toast Utility
export function showToast(message, type = 'info') {
  const container = $('#toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
    <div>${message}</div>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Formatters
function formatConfidence(val) {
  if (val === null || val === undefined) return 'N/A';
  const percent = Math.round(val * 100);
  let colorClass = 'confidence-high';
  if (percent < 70) colorClass = 'confidence-low';
  else if (percent < 85) colorClass = 'confidence-med';
  return { percent, colorClass };
}

function formatBadge(status) {
  const s = (status || 'pending').toLowerCase();
  return `<span class="badge badge-${s}">${s.toUpperCase()}</span>`;
}

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupAuthEvents();
  setupUploadEvents();
  setupStudioEvents();
  setupGroupsEvents();
  setupHealthEvents();

  // Display active API Base in navbar badge
  const apiLabel = $('#nav-api-url');
  if (apiLabel) apiLabel.textContent = api.apiBase;
  const apiBadge = $('#nav-api-badge');
  if (apiBadge) {
    apiBadge.addEventListener('click', async () => {
      const custom = prompt('Configure Backend API Server URL (e.g. http://localhost:8000/api/v1):', api.apiBase);
      if (custom && custom.trim()) {
        api.setApiBase(custom.trim());
        if (apiLabel) apiLabel.textContent = api.apiBase;
        showToast(`Connected to API: ${api.apiBase}`, 'success');
        if (api.token) {
          await loadDashboard();
        }
        await loadHealth();
      }
    });
  }

  // Check initial authentication
  await refreshAuthUI();

  // If already authenticated, load dashboard
  if (api.token) {
    await loadDashboard();
  } else {
    // Open auth modal immediately for smooth onboarding
    openAuthModal();
  }
});

// Authentication Handlers
async function refreshAuthUI() {
  const userProfile = $('#nav-user-profile');
  const loginBtn = $('#nav-login-btn');

  if (api.token && api.currentUser) {
    userProfile.style.display = 'flex';
    loginBtn.style.display = 'none';
    $('#user-display-email').textContent = api.currentUser.email;
    $('#user-display-role').textContent = api.currentUser.role.toUpperCase();
    $('#user-display-avatar').textContent = api.currentUser.email[0].toUpperCase();
  } else {
    userProfile.style.display = 'none';
    loginBtn.style.display = 'inline-flex';
  }
}

function openAuthModal() {
  $('#auth-modal').classList.add('active');
}

function closeAuthModal() {
  $('#auth-modal').classList.remove('active');
}

function setupAuthEvents() {
  $('#nav-login-btn').addEventListener('click', openAuthModal);
  $('#auth-modal-close').addEventListener('click', closeAuthModal);
  $('#nav-logout-btn').addEventListener('click', () => {
    api.clearAuth();
    refreshAuthUI();
    showToast('Logged out successfully.', 'info');
    openAuthModal();
  });

  // Switch between Login and Register tabs
  $$('.auth-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.auth-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tab = btn.dataset.tab;
      if (tab === 'login') {
        $('#login-form').style.display = 'block';
        $('#register-form').style.display = 'none';
      } else {
        $('#login-form').style.display = 'none';
        $('#register-form').style.display = 'block';
      }
    });
  });

  // 1-Click Persona Login buttons
  $$('.persona-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const email = btn.dataset.email;
      const pass = btn.dataset.pass;
      try {
        btn.style.opacity = '0.5';
        const { user } = await api.login(email, pass);
        showToast(`Signed in as ${user.role} (${user.email})!`, 'success');
        closeAuthModal();
        await refreshAuthUI();
        await loadDashboard();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.style.opacity = '1';
      }
    });
  });

  // Regular Login submit
  $('#login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = $('#login-email').value.trim();
    const password = $('#login-password').value;
    try {
      const { user } = await api.login(email, password);
      showToast(`Welcome back, ${user.email}!`, 'success');
      closeAuthModal();
      await refreshAuthUI();
      await loadDashboard();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Regular Register submit
  $('#register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = $('#reg-email').value.trim();
    const password = $('#reg-password').value;
    const role = $('#reg-role').value;
    try {
      await api.register(email, password, role);
      showToast('Registration successful! Logging in...', 'success');
      const { user } = await api.login(email, password);
      closeAuthModal();
      await refreshAuthUI();
      await loadDashboard();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  window.addEventListener('auth-expired', () => {
    refreshAuthUI();
    openAuthModal();
  });
}

// Navigation & Tab Switching
function setupNavigation() {
  $$('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      const target = link.dataset.target;
      switchTab(target);
    });
  });
}

export function switchTab(tabId) {
  $$('.nav-link').forEach(l => l.classList.remove('active'));
  const activeLink = $(`[data-target="${tabId}"]`);
  if (activeLink) activeLink.classList.add('active');

  $$('.view-section').forEach(sec => sec.classList.remove('active'));
  const activeSec = $(`#view-${tabId}`);
  if (activeSec) activeSec.classList.add('active');

  state.currentTab = tabId;

  if (tabId === 'dashboard') loadDashboard();
  if (tabId === 'studio') loadStudio();
  if (tabId === 'groups') loadGroups();
  if (tabId === 'health') loadHealth();
}

// Dashboard Module
async function loadDashboard() {
  if (!api.token) return;
  try {
    const res = await api.listDocuments(1, 50, state.activeFilterStatus);
    state.documents = res.items || [];

    // Render Metrics
    $('#metric-doc-count').textContent = state.documents.length;
    let totalQuestions = 0;
    state.documents.forEach(d => {
      if (d.doc_metadata && d.doc_metadata.question_count) {
        totalQuestions += d.doc_metadata.question_count;
      }
    });
    $('#metric-q-count').textContent = totalQuestions || (state.documents.length * 4);

    renderDocumentTable(state.documents);
    setupPollingIfNeeded();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderDocumentTable(docs) {
  const tbody = $('#doc-table-body');
  if (!tbody) return;

  if (docs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 3rem; color: var(--text-muted);">
          No documents found. Click <strong>Upload Document</strong> to ingest your first question paper!
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = docs.map(doc => {
    const filename = doc.original_filename || doc.filename || 'Untitled Document';
    const pages = doc.page_count ? `${doc.page_count} pg` : '1 pg';
    const date = new Date(doc.created_at).toLocaleDateString();
    const duration = doc.timings && doc.timings.total_duration_seconds
      ? `${doc.timings.total_duration_seconds.toFixed(1)}s`
      : (doc.processing_time_seconds ? `${doc.processing_time_seconds.toFixed(1)}s` : '--');

    return `
      <tr>
        <td>
          <div style="display: flex; flex-direction: column;">
            <strong style="color: var(--text-primary);">${filename}</strong>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${doc.id.substring(0, 8)}...</span>
          </div>
        </td>
        <td>${pages}</td>
        <td>${formatBadge(doc.status)}</td>
        <td>${duration}</td>
        <td>${date}</td>
        <td>
          <div style="display: flex; align-items: center; gap: 0.4rem;">
            <button class="btn btn-secondary btn-sm" onclick="window.inspectDocument('${doc.id}')" title="Inspect Questions">
              🔍 Inspect
            </button>
            <div style="position: relative; display: inline-block;">
              <button class="btn btn-secondary btn-sm" onclick="window.toggleExportDropdown('${doc.id}')" title="Export Formats">
                📥 Export ▾
              </button>
              <div id="export-menu-${doc.id}" class="card-panel" style="display: none; position: absolute; right: 0; top: 100%; z-index: 50; padding: 0.5rem; min-width: 120px; box-shadow: var(--shadow-lg);">
                <button class="btn btn-sm" style="width: 100%; text-align: left;" onclick="window.downloadDoc('${doc.id}', 'json')">JSON</button>
                <button class="btn btn-sm" style="width: 100%; text-align: left;" onclick="window.downloadDoc('${doc.id}', 'csv')">CSV</button>
                <button class="btn btn-sm" style="width: 100%; text-align: left;" onclick="window.downloadDoc('${doc.id}', 'docx')">DOCX</button>
              </div>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="window.reprocessDoc('${doc.id}')" title="Reprocess">
              🔄
            </button>
            <button class="btn btn-secondary btn-sm" style="color: var(--danger);" onclick="window.deleteDoc('${doc.id}')" title="Delete">
              🗑
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// Global actions for inline table buttons
window.inspectDocument = (id) => {
  state.selectedDocId = id;
  switchTab('studio');
};

window.toggleExportDropdown = (id) => {
  const menu = $(`#export-menu-${id}`);
  if (menu) {
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  }
};

window.downloadDoc = async (id, format) => {
  try {
    const res = await api.exportDocument(id, format);
    let blob;
    if (format === 'json') {
      blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
    } else {
      blob = res instanceof Blob ? res : new Blob([res]);
    }
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `document_${id.substring(0, 8)}_export.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast(`Exported ${format.toUpperCase()} successfully!`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.reprocessDoc = async (id) => {
  try {
    await api.reprocessDocument(id);
    showToast('Reprocessing triggered!', 'info');
    await loadDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.deleteDoc = async (id) => {
  if (!confirm('Are you sure you want to delete this document?')) return;
  try {
    await api.deleteDocument(id);
    showToast('Document deleted.', 'info');
    await loadDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

function setupPollingIfNeeded() {
  const isAnyProcessing = state.documents.some(d => d.status === 'processing' || d.status === 'queued');
  if (isAnyProcessing && !state.pollingInterval) {
    state.pollingInterval = setInterval(async () => {
      if (state.currentTab === 'dashboard') {
        const res = await api.listDocuments(1, 50, state.activeFilterStatus);
        state.documents = res.items || [];
        renderDocumentTable(state.documents);
        const stillProcessing = state.documents.some(d => d.status === 'processing' || d.status === 'queued');
        if (!stillProcessing) {
          clearInterval(state.pollingInterval);
          state.pollingInterval = null;
        }
      }
    }, 3000);
  } else if (!isAnyProcessing && state.pollingInterval) {
    clearInterval(state.pollingInterval);
    state.pollingInterval = null;
  }
}

// Ingest / Upload Module
function setupUploadEvents() {
  const dropzone = $('#upload-dropzone');
  const fileInput = $('#upload-file-input');

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleFileUpload(fileInput.files[0]);
    }
  });
}

async function handleFileUpload(file) {
  if (!api.token) {
    showToast('Please sign in before uploading documents.', 'error');
    openAuthModal();
    return;
  }

  const examName = $('#upload-exam-name').value.trim() || file.name;
  const subject = $('#upload-subject').value.trim() || 'General';
  const year = parseInt($('#upload-year').value) || 2026;

  const metadata = { exam_name: examName, subject, year };

  const btn = $('#upload-submit-btn');
  btn.disabled = true;
  btn.textContent = 'Uploading & Initializing Pipeline...';

  try {
    const res = await api.uploadDocument(file, metadata);
    showToast(`Uploaded "${file.name}"! Pipeline is extracting questions.`, 'success');
    state.selectedDocId = res.document_id || res.id;
    // Switch to Dashboard to watch processing
    switchTab('dashboard');
    await loadDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload & Process Document';
    $('#upload-file-input').value = '';
  }
}

// Question Intelligence Studio Module
async function loadStudio() {
  if (!api.token) return;

  try {
    // Always refresh documents to display the most current statuses
    const docsRes = await api.listDocuments(1, 100);
    state.documents = docsRes.items || [];
  } catch (_) {}

  // Wire up the manual refresh button in Question Studio header
  const refreshBtn = $('#studio-refresh-btn');
  if (refreshBtn && !refreshBtn.dataset.bound) {
    refreshBtn.dataset.bound = 'true';
    refreshBtn.addEventListener('click', async () => {
      refreshBtn.style.opacity = '0.5';
      await loadStudio();
      showToast('Document and questions refreshed!', 'info');
      refreshBtn.style.opacity = '1';
    });
  }

  // Populate document picker dropdown
  const selector = $('#studio-doc-select');
  if (!selector) return;

  selector.innerHTML = state.documents.map(d => {
    const name = d.original_filename || d.filename || ('Document ' + d.id.substring(0, 8));
    const stat = (d.status || 'uploaded').toUpperCase();
    return `
      <option value="${d.id}" ${d.id === state.selectedDocId ? 'selected' : ''}>
        ${name} (${stat})
      </option>
    `;
  }).join('');

  if (!state.selectedDocId && state.documents.length > 0) {
    state.selectedDocId = state.documents[0].id;
    selector.value = state.selectedDocId;
  }

  selector.onchange = () => {
    state.selectedDocId = selector.value;
    loadQuestionsForDoc(state.selectedDocId);
  };

  if (state.selectedDocId) {
    selector.value = state.selectedDocId;
    await loadQuestionsForDoc(state.selectedDocId);
  } else {
    renderEmptyStudio();
  }
}

async function loadQuestionsForDoc(docId) {
  if (state.studioPollingInterval) {
    clearInterval(state.studioPollingInterval);
    state.studioPollingInterval = null;
  }

  const activeDoc = state.documents.find(d => d.id === docId);
  const isPending = activeDoc && (activeDoc.status === 'queued' || activeDoc.status === 'processing');

  const container = $('#studio-question-list');

  // If document is currently processing, show live progress and poll until finished
  if (isPending) {
    if (container) {
      container.innerHTML = `
        <div style="color: var(--accent-secondary); text-align: center; padding: 2.5rem 1rem;">
          <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">⏳</div>
          <h4 style="color: var(--text-primary); font-size: 0.95rem;">Extraction In Progress</h4>
          <div style="margin-top: 0.4rem; font-size: 0.8rem; color: var(--text-secondary);">
            Status: <span class="badge badge-queued">${activeDoc.status.toUpperCase()}</span>
          </div>
          <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.6rem; line-height: 1.4;">
            Analyzing page layouts, OCR text, and diagrams... Questions will appear automatically.
          </p>
        </div>
      `;
    }
    renderEmptyStudio();

    state.studioPollingInterval = setInterval(async () => {
      if (state.currentTab !== 'studio' || state.selectedDocId !== docId) {
        clearInterval(state.studioPollingInterval);
        state.studioPollingInterval = null;
        return;
      }

      try {
        const statusRes = await api.getDocumentStatus(docId);
        if (statusRes.status !== 'queued' && statusRes.status !== 'processing') {
          clearInterval(state.studioPollingInterval);
          state.studioPollingInterval = null;
          // Refresh documents and studio once complete
          await loadStudio();
        }
      } catch (_) {}
    }, 2000);
    return;
  }

  try {
    const res = await api.listQuestions(docId, 1, 100);
    state.questions = res.items || [];
    renderQuestionsSidebar(state.questions);

    if (state.questions.length > 0) {
      selectQuestion(state.questions[0].id);
    } else {
      renderEmptyStudio();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderQuestionsSidebar(questions) {
  const container = $('#studio-question-list');
  if (!container) return;

  if (questions.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No questions extracted for this document.</div>`;
    return;
  }

  container.innerHTML = questions.map((q, idx) => {
    const num = q.question_number || (idx + 1);
    const confVal = q.confidence !== undefined ? q.confidence : q.confidence_score;
    const { percent, colorClass } = formatConfidence(confVal);
    const snippet = q.question_text || 'No text';
    const isActive = q.id === state.selectedQuestionId;
    const qType = (q.question_type || 'MCQ').toUpperCase();
    const statusVal = (q.review && q.review.status) || q.review_status || q.status;

    return `
      <div class="question-card-item ${isActive ? 'active' : ''}" onclick="window.selectQuestion('${q.id}')">
        <div class="q-card-top">
          <span class="q-card-title">Question ${num}</span>
          <span class="badge ${colorClass === 'confidence-high' ? 'badge-completed' : 'badge-queued'}">${percent}% Conf</span>
        </div>
        <div class="q-card-snippet">${snippet}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.2rem;">
          <span style="font-size: 0.68rem; color: var(--accent-secondary); font-weight: 600;">${qType}</span>
          ${formatBadge(statusVal)}
        </div>
      </div>
    `;
  }).join('');
}

window.selectQuestion = (id) => {
  state.selectedQuestionId = id;
  // Highlight in sidebar
  $$('.question-card-item').forEach(el => el.classList.remove('active'));
  const activeEl = $(`[onclick="window.selectQuestion('${id}')"]`);
  if (activeEl) activeEl.classList.add('active');

  const q = state.questions.find(x => x.id === id);
  if (q) renderQuestionDetail(q);
};

function renderQuestionDetail(q) {
  const panel = $('#studio-detail-panel');
  if (!panel) return;

  const confVal = q.confidence !== undefined ? q.confidence : q.confidence_score;
  const { percent, colorClass } = formatConfidence(confVal);
  const options = Array.isArray(q.options) ? q.options : [];
  const statusVal = (q.review && q.review.status) || q.review_status || q.status;
  const qType = (q.question_type || 'mcq_single').toUpperCase();

  // Extract correct answers from schema
  const correctAnswers = [];
  if (q.answer && Array.isArray(q.answer.value)) {
    correctAnswers.push(...q.answer.value);
  } else if (q.answer && q.answer.raw) {
    correctAnswers.push(q.answer.raw);
  }
  if (q.correct_answer) {
    correctAnswers.push(q.correct_answer);
  }

  const rawKeyText = q.answer && q.answer.raw ? q.answer.raw : (correctAnswers.join(', ') || 'None');
  const reviewer = (q.review && q.review.reviewed_by)
    || (q.reviewer_id ? q.reviewer_id.substring(0, 8) : 'Pending Review');

  panel.innerHTML = `
    <div class="detail-header-row">
      <div>
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <h2>Question ${q.question_number || 'N/A'}</h2>
          <span class="badge" style="background: #fef9c3; color: #854d0e; border: 1px solid #fde047; font-weight: 700;">${qType}</span>
          ${formatBadge(statusVal)}
        </div>
        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem;">
          Extracted Answer Key: <span class="mono" style="color: var(--accent-secondary); font-weight: 600;">${rawKeyText}</span>
        </div>
      </div>
      <div class="confidence-meter-container">
        <div style="text-align: right;">
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Confidence</div>
          <div style="font-weight: 700; font-size: 1.1rem; color: var(--text-primary);">${percent}%</div>
        </div>
        <div class="confidence-bar-outer">
          <div class="confidence-bar-inner ${colorClass}" style="width: ${percent}%;"></div>
        </div>
      </div>
    </div>

    <div>
      <h4 style="font-size: 0.82rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem;">Question Text</h4>
      <div class="question-text-box">${q.question_text || 'No text extracted.'}</div>
    </div>

    ${options.length > 0 ? `
      <div>
        <h4 style="font-size: 0.82rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.75rem;">Options & Answer Key</h4>
        <div class="options-container">
          ${options.map((opt, i) => {
            const optLabel = opt.label || opt.key || String.fromCharCode(65 + i);
            const isCorrect = correctAnswers.some(ans => ans.trim().toLowerCase() === optLabel.trim().toLowerCase());
            return `
              <div class="option-row ${isCorrect ? 'is-correct' : ''}">
                <div class="option-key">${optLabel}</div>
                <div class="option-text">${opt.text || ''}</div>
                ${isCorrect ? '<span class="badge badge-completed">✓ CORRECT OPTION</span>' : ''}
              </div>
            `;
          }).join('')}
        </div>
      </div>
    ` : ''}

    ${q.explanation || (q.review && q.review.notes) ? `
      <div style="background: #fefce8; border: 1px solid #fef08a; border-radius: var(--radius-md); padding: 1rem;">
        <h4 style="font-size: 0.82rem; color: #ca8a04; margin-bottom: 0.4rem;">Review Notes & Explanation</h4>
        <div style="font-size: 0.88rem; color: #334155;">${q.explanation || (q.review && q.review.notes)}</div>
      </div>
    ` : ''}

    <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--border-subtle); padding-top: 1.5rem; margin-top: auto;">
      <div style="font-size: 0.78rem; color: var(--text-muted);">
        Reviewer: ${reviewer}
      </div>
      <div style="display: flex; gap: 0.75rem;">
        <button class="btn btn-secondary btn-sm" onclick="window.openEditQuestionModal('${q.id}')">
          ✏️ Edit & Correct
        </button>
        <button class="btn btn-danger btn-sm" onclick="window.triggerReviewAction('${q.id}', 'reject')">
          ✕ Reject
        </button>
        <button class="btn btn-success btn-sm" onclick="window.triggerReviewAction('${q.id}', 'approve')">
          ✓ Approve
        </button>
      </div>
    </div>
  `;
}

function renderEmptyStudio() {
  $('#studio-detail-panel').innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); text-align: center;">
      <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
      <h3>No Questions Selected</h3>
      <p style="font-size: 0.88rem; max-width: 320px; margin-top: 0.5rem;">
        Select an extracted document from the dropdown above to inspect and edit questions.
      </p>
    </div>
  `;
}

function setupStudioEvents() {
  $('#edit-question-close').addEventListener('click', () => {
    $('#edit-question-modal').classList.remove('active');
  });

  $('#edit-question-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = state.selectedQuestionId;
    const text = $('#edit-q-text').value;
    const correctAns = $('#edit-q-answer').value.trim();
    const explanation = $('#edit-q-explanation').value.trim();

    try {
      const updateData = {
        question_text: text,
      };
      if (correctAns) {
        updateData.answer = {
          value: correctAns.split(',').map(s => s.trim().toUpperCase()),
          raw: correctAns,
          match_status: 'matched',
          confidence: 1.0,
        };
      }
      if (explanation) {
        updateData.notes = explanation;
      }
      await api.updateQuestion(id, updateData);
      showToast('Question updated and saved!', 'success');
      $('#edit-question-modal').classList.remove('active');
      await loadQuestionsForDoc(state.selectedDocId);
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

window.openEditQuestionModal = (id) => {
  const q = state.questions.find(x => x.id === id);
  if (!q) return;

  $('#edit-q-text').value = q.question_text || '';
  const ansVal = (q.answer && Array.isArray(q.answer.value) ? q.answer.value.join(', ') : (q.answer && q.answer.raw))
    || q.correct_answer || '';
  $('#edit-q-answer').value = ansVal;
  $('#edit-q-explanation').value = q.explanation || (q.review && q.review.notes) || '';
  $('#edit-question-modal').classList.add('active');
};

window.triggerReviewAction = async (id, action) => {
  const normalizedAction = action.toLowerCase().startsWith('app') ? 'approve' : 'reject';
  const notes = prompt(`Enter review notes for ${normalizedAction.toUpperCase()}:`, `Reviewed via Web UI`);
  if (notes === null) return;

  try {
    await api.reviewQuestion(id, normalizedAction, notes);
    showToast(`Question marked as ${normalizedAction}d!`, 'success');
    await loadQuestionsForDoc(state.selectedDocId);
  } catch (err) {
    showToast(err.message, 'error');
  }
};

// Groups & Answer Keys Module
async function loadGroups() {
  if (!api.token) return;
  try {
    const res = await api.listGroups();
    const groups = Array.isArray(res) ? res : (res.items || []);
    const container = $('#groups-list-container');
    if (!container) return;

    if (groups.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No document groups created yet. Create one to link separate question papers with answer keys!</div>`;
      return;
    }

    container.innerHTML = groups.map(g => {
      const docCount = (g.documents && g.documents.length) || 0;
      return `
        <div class="card-panel" style="margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between;">
          <div>
            <h3>${g.name}</h3>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.2rem;">${g.description || 'No description'} (${docCount} attached documents)</p>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-primary btn-sm" onclick="window.mergeGroup('${g.id}')">
              🔗 Auto-Merge Questions & Key
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function setupGroupsEvents() {
  $('#create-group-btn').addEventListener('click', async () => {
    const name = prompt('Enter Group Name:');
    if (!name) return;
    const description = prompt('Enter Description:');
    try {
      await api.createGroup(name, description || '');
      showToast('Group created!', 'success');
      await loadGroups();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

window.mergeGroup = async (id) => {
  try {
    const res = await api.mergeGroup(id);
    showToast(`Merged group successfully! Extracted answers paired.`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
};

// System Health Module
async function loadHealth() {
  try {
    const health = await api.getHealth();
    $('#health-status-badge').innerHTML = health.status === 'ready' 
      ? '<span class="badge badge-completed">SYSTEM READY (100% OPERATIONAL)</span>'
      : '<span class="badge badge-queued">DEGRADED</span>';
    
    $('#health-db-status').textContent = health.checks.database || 'healthy';
    $('#health-redis-status').textContent = health.checks.redis || 'active';
  } catch (err) {
    $('#health-status-badge').innerHTML = '<span class="badge badge-rejected">UNAVAILABLE</span>';
  }
}

function setupHealthEvents() {
  $('#refresh-health-btn').addEventListener('click', loadHealth);
}

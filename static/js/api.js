// Pragati Bharti API Client Layer

export const getApiBase = () => {
  // 1. Check if user configured a custom base URL in localStorage
  const saved = localStorage.getItem('pragati_api_base');
  if (saved) return saved.replace(/\/+$/, '');

  // 2. If running on a static server (e.g. VS Code Live Server on :5500, Vite on :5173, etc.),
  // automatically target the backend at port 8000
  if (typeof window !== 'undefined' && window.location && window.location.port && window.location.port !== '8000') {
    const hostname = window.location.hostname || 'localhost';
    return `http://${hostname}:8000/api/v1`;
  }
  return '/api/v1';
};

export const API_BASE = getApiBase();

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('pragati_token') || null;
    this.currentUser = JSON.parse(localStorage.getItem('pragati_user') || 'null');
    this.apiBase = API_BASE;
  }

  setApiBase(url) {
    this.apiBase = url.replace(/\/+$/, '');
    localStorage.setItem('pragati_api_base', this.apiBase);
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('pragati_token', token);
  }

  setCurrentUser(user) {
    this.currentUser = user;
    localStorage.setItem('pragati_user', JSON.stringify(user));
  }

  clearAuth() {
    this.token = null;
    this.currentUser = null;
    localStorage.removeItem('pragati_token');
    localStorage.removeItem('pragati_user');
  }

  getHeaders(isMultipart = false) {
    const headers = {};
    if (!isMultipart) {
      headers['Content-Type'] = 'application/json';
    }
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const isMultipart = options.body instanceof FormData;
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${this.apiBase}${cleanEndpoint}`;
    const headers = {
      ...this.getHeaders(isMultipart),
      ...(options.headers || {}),
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        this.clearAuth();
        window.dispatchEvent(new CustomEvent('auth-expired'));
        throw new Error('Session expired or unauthorized. Please log in again.');
      }

      if (!response.ok) {
        let errMessage = `Error ${response.status}: ${response.statusText}`;
        try {
          const errData = await response.json();
          errMessage = errData.detail || errData.message || (errData.error && errData.error.message) || errMessage;
        } catch (_) {}
        throw new Error(errMessage);
      }

      // Check if response is JSON or blob (export)
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        return await response.json();
      } else if (contentType.includes('text/csv') || contentType.includes('application/vnd')) {
        return await response.blob();
      }
      return await response.text();
    } catch (err) {
      console.error(`API Call failed on ${endpoint}:`, err);
      throw err;
    }
  }

  // Authentication
  async login(email, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token);
    const user = await this.getMe();
    this.setCurrentUser(user);
    return { token: res.access_token, user };
  }

  async register(email, password, role = 'user') {
    return await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, role }),
    });
  }

  async getMe() {
    return await this.request('/auth/me');
  }

  // Documents
  async listDocuments(page = 1, pageSize = 20, status = '') {
    let q = `?page=${page}&limit=${pageSize}`;
    if (status) q += `&status=${encodeURIComponent(status)}`;
    return await this.request(`/documents${q}`);
  }

  async getDocument(id) {
    return await this.request(`/documents/${id}`);
  }

  async getDocumentStatus(id) {
    return await this.request(`/documents/${id}/status`);
  }

  async uploadDocument(file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));
    return await this.request('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  }

  async reprocessDocument(id) {
    return await this.request(`/documents/${id}/reprocess`, {
      method: 'POST',
    });
  }

  async exportDocument(id, format = 'json') {
    return await this.request(`/documents/${id}/export?format=${format}`);
  }

  async deleteDocument(id) {
    return await this.request(`/documents/${id}`, {
      method: 'DELETE',
    });
  }

  // Questions
  async listQuestions(documentId, page = 1, pageSize = 50, reviewStatus = '', confidenceMin = null) {
    let q = `?page=${page}&limit=${pageSize}`;
    if (reviewStatus) q += `&status=${encodeURIComponent(reviewStatus)}`;
    if (confidenceMin !== null) q += `&min_confidence=${confidenceMin}`;
    return await this.request(`/documents/${documentId}/questions${q}`);
  }

  async getQuestion(id) {
    return await this.request(`/questions/${id}`);
  }

  async updateQuestion(id, updateData) {
    return await this.request(`/questions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updateData),
    });
  }

  async reviewQuestion(id, action, notes = '', correctedData = null) {
    const payload = { action, notes };
    if (correctedData) {
      payload.corrected_data = correctedData;
    }
    return await this.request(`/questions/${id}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async deleteQuestion(id) {
    return await this.request(`/questions/${id}`, {
      method: 'DELETE',
    });
  }

  // Answer Keys & Groups
  async listAnswers(documentId) {
    return await this.request(`/documents/${documentId}/answer-key`);
  }

  async listGroups(page = 1, pageSize = 20) {
    return await this.request(`/groups`);
  }

  async createGroup(name, description = '') {
    return await this.request('/groups', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
  }

  async linkDocumentToGroup(groupId, documentId, role = 'question_paper') {
    return await this.request(`/groups/${groupId}/documents`, {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId, role }),
    });
  }

  async mergeGroup(groupId) {
    try {
      return await this.request(`/groups/${groupId}/merge`, {
        method: 'POST',
      });
    } catch (_) {
      // Fallback to fetching merged questions
      return await this.request(`/groups/${groupId}/questions`);
    }
  }

  // Quality Warnings & Health
  async listWarnings(documentId) {
    return await this.request(`/documents/${documentId}/warnings`);
  }

  async getHealth() {
    return await this.request('/health/ready');
  }
}

export const api = new ApiClient();


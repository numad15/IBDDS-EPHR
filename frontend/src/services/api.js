/**
 * API Service Layer
 * Handles all HTTP requests to the Flask backend.
 */

// Allow overriding API base (useful for Docker/production); default works with Vite dev proxy.
const API_BASE = import.meta.env.VITE_API_BASE || '/api';

class ApiService {
  constructor() {
    this.token = localStorage.getItem('ibdds_token');
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('ibdds_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('ibdds_token');
    localStorage.removeItem('ibdds_user');
  }

  getUser() {
    const user = localStorage.getItem('ibdds_user');
    return user ? JSON.parse(user) : null;
  }

  setUser(user) {
    localStorage.setItem('ibdds_user', JSON.stringify(user));
  }

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Request failed');
    }

    return data;
  }

  // Auth
  async register(email, password, role) {
    return this.request('/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, role }),
    });
  }

  async login(email, password) {
    const data = await this.request('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.token);
    this.setUser(data.user);
    return data;
  }

  logout() {
    this.clearToken();
  }

  // EPHR Records
  async uploadRecord(healthData) {
    return this.request('/ephr/upload', {
      method: 'POST',
      body: JSON.stringify({ health_data: healthData }),
    });
  }

  async listRecords() {
    return this.request('/ephr/records');
  }

  async getRecord(recordId) {
    return this.request(`/ephr/${recordId}`);
  }

  // Access Grants
  async grantAccess(accessorEmail, accessTypes, resourceFields, durationDays) {
    return this.request('/access/grant', {
      method: 'POST',
      body: JSON.stringify({
        accessor_email: accessorEmail,
        access_types: accessTypes,
        resource_fields: resourceFields,
        duration_days: durationDays,
      }),
    });
  }

  async revokeAccess(grantId) {
    return this.request('/access/revoke', {
      method: 'POST',
      body: JSON.stringify({ grant_id: grantId }),
    });
  }

  async listGrants() {
    return this.request('/access/grants');
  }

  // Audit
  async getAuditLogs(patientId = null, action = null) {
    let query = '';
    const params = [];
    if (patientId) params.push(`patient_id=${patientId}`);
    if (action) params.push(`action=${action}`);
    if (params.length) query = '?' + params.join('&');
    return this.request(`/audit${query}`);
  }

  // System
  async getDoctors() {
    return this.request('/doctors');
  }

  async getSystemStatus() {
    return this.request('/system/status');
  }
}

const api = new ApiService();
export default api;

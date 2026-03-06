const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('heraldo_token');
}

function getHeaders(includeAuth = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (includeAuth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchLimits() {
  const res = await fetch(`${API_BASE}/limits`);
  if (!res.ok) throw new Error('Failed to fetch limits');
  return res.json();
}

/** Authenticated: returns effective limits for current user (per-user overrides). */
export async function fetchUserLimits() {
  const res = await fetch(`${API_BASE}/user/limits`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch limits');
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: getHeaders(false),
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Login failed');
  return data;
}

export async function register(fullName, password, email) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: getHeaders(false),
    body: JSON.stringify({ full_name: fullName, password, email }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Error al registrarse');
  return data;
}

export async function verifyEmail(token) {
  const res = await fetch(`${API_BASE}/auth/verify-email?token=${encodeURIComponent(token)}`, {
    method: 'GET',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Error al verificar');
  return data;
}

export async function changePassword(currentPassword, newPassword) {
  const res = await fetch(`${API_BASE}/auth/change-password`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to change password');
  return data;
}

export async function fetchMe() {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Not authenticated');
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/user/stats`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/pdf`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function fetchDocumentStatus(id) {
  const res = await fetch(`${API_BASE}/pdf/${id}/status`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function countPdfWords(file) {
  const formData = new FormData();
  formData.append('file', file);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000); // 90s
  try {
    const res = await fetch(`${API_BASE}/pdf/count-words`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Error al contar palabras');
    return data;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('El archivo tardó demasiado. Prueba con un PDF más pequeño o con menos páginas.');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/pdf/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}` },
    body: formData,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || 'Upload failed');
    if (data.word_count != null) err.wordCount = data.word_count;
    throw err;
  }
  return data;
}

export async function getPlayToken(id) {
  const res = await fetch(`${API_BASE}/pdf/${id}/play-token`, {
    method: 'POST',
    headers: getHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to get play token');
  return data.token;
}

/** Stream URL for in-browser playback (no full download). Token valid 1h. */
export function getStreamUrl(id, token) {
  return `/api/pdf/${id}/stream?t=${encodeURIComponent(token)}`;
}

export async function getPdfViewToken(id) {
  const res = await fetch(`${API_BASE}/pdf/${id}/view-pdf-token`, {
    method: 'POST',
    headers: getHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to get view token');
  return data.token;
}

/** URL to view the uploaded PDF in a new tab. Token valid 1h. */
export function getPdfViewUrl(id, token) {
  return `/api/pdf/${id}/view?t=${encodeURIComponent(token)}`;
}

// --- Admin API ---
export async function adminListUsers() {
  const res = await fetch(`${API_BASE}/admin/users`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch users');
  return res.json();
}

export async function adminGetUser(userId) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch user');
  return res.json();
}

export async function adminUpdateUserLimits(userId, payload) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}/limits`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || 'Failed to update limits');
  }
  return res.json();
}

export async function adminListUserDocuments(userId) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}/documents`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function adminGetPlayToken(userId, docId) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}/documents/${docId}/play-token`, {
    method: 'POST',
    headers: getHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to get play token');
  return data.token;
}

export async function adminGetPdfViewToken(userId, docId) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}/documents/${docId}/view-pdf-token`, {
    method: 'POST',
    headers: getHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to get view token');
  return data.token;
}

export async function downloadAudio(id, filename) {
  const res = await fetch(`${API_BASE}/pdf/${id}/download`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error('Download failed');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || 'audio.mp3';
  a.click();
  window.URL.revokeObjectURL(url);
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function sendChatMessage(message, threadId, model) {
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId, model }),
  });
  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server returned HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function getLiveWeather(city) {
  const resp = await fetch(`${API_BASE}/api/weather?city=${encodeURIComponent(city)}`);
  if (!resp.ok) throw new Error('Failed to retrieve weather');
  return resp.json();
}

export async function getSOPs() {
  const resp = await fetch(`${API_BASE}/api/sops`);
  if (!resp.ok) throw new Error('Failed to retrieve SOPs');
  return resp.json();
}

export async function reloadSOPs() {
  const resp = await fetch(`${API_BASE}/api/sops/reload`, { method: 'POST' });
  if (!resp.ok) throw new Error('Failed to reload SOPs');
  return resp.json();
}

export async function createOrUpdateSOP(sopData) {
  const resp = await fetch(`${API_BASE}/api/sops`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sopData),
  });
  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server returned HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function deleteSOP(sopId) {
  const resp = await fetch(`${API_BASE}/api/sops/${encodeURIComponent(sopId)}`, {
    method: 'DELETE',
  });
  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server returned HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function getHealth() {
  const resp = await fetch(`${API_BASE}/api/health`);
  if (!resp.ok) throw new Error('Failed to retrieve health status');
  return resp.json();
}

export async function getAvailableModels() {
  const resp = await fetch(`${API_BASE}/api/models`);
  if (!resp.ok) throw new Error('Failed to retrieve available models');
  return resp.json();
}

export async function getChatSession(threadId) {
  const resp = await fetch(`${API_BASE}/api/chat/${encodeURIComponent(threadId)}`);
  if (!resp.ok) {
    if (resp.status === 404) return null;
    throw new Error('Failed to retrieve chat session');
  }
  return resp.json();
}

export async function syncChatSession(threadId, title, model, messages) {
  const resp = await fetch(`${API_BASE}/api/chat/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, title, model, messages }),
  });
  if (!resp.ok) return null;
  return resp.json();
}





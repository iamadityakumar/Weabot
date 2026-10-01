const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function sendChatMessage(message, threadId) {
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
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

export async function getHealth() {
  const resp = await fetch(`${API_BASE}/api/health`);
  if (!resp.ok) throw new Error('Failed to retrieve health status');
  return resp.json();
}

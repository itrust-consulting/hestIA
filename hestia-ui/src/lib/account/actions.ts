import { api } from '$lib/api/client';

export async function getAccountDetails() {
  const res = await api.get('/api/account');
  if (!res.ok) throw new Error(`Failed to load account info: ${res.status}`);
  return await res.json();
}

export async function changePassword(current: string, next: string) {
  const res = await api.patch('/api/account/password', {
    current_pw: current,
    new_pw: next
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? 'Password update failed.');
  }

  return await res.json();
}

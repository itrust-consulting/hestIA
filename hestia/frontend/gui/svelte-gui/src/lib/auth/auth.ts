// src/lib/auth/auth.ts

export async function login(email: string, password: string) {
  try {
    return { ok: true };
  } catch (e) {
    return { ok: false, error: 'Network error' };
  }
}
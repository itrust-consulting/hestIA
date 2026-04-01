import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555'
const LOGIN_API = API_URL + '/login'

export async function POST({ request, cookies }) {
  const { username, password } = await request.json();

  const res = await fetch(LOGIN_API, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({ username, password })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed.' }));
    return json({ ok: false, error: err.detail }, { status: 401 });
  }

  const data = await res.json();

  cookies.set('token', data.access_token, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 // 1 hour
  });

  return json({ 
    ok: true, 
    must_change_pw: data.must_change_pw ?? false
  });
}
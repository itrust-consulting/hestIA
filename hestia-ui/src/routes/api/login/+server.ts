import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { jwtDecode } from 'jwt-decode';
import { redirect } from '@sveltejs/kit';

const API_URL = env.PRIVATE_MICROSERVICE_URL || 'http://localhost:5555'
const LOGIN_API = API_URL + '/login'

export async function POST({ request, cookies, url }) {
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

  const decoded: any = jwtDecode(data.access_token);
  const exp: number = decoded.exp;

  cookies.set('token', data.access_token, {
    httpOnly: true,
    secure: url.protocol === 'https:',
    sameSite: 'lax',
    path: '/',
    maxAge: exp - Math.floor(Date.now() / 1000)
  });

  return json({ 
    ok: true, 
    must_change_pw: data.must_change_pw ?? false,
    exp: exp
  });
}
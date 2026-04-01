import { json } from '@sveltejs/kit';

export async function POST({ cookies }) {
  // Delete the token cookie
  cookies.delete('token', {
    path: '/', 
    sameSite: 'lax'
  });

  return json({ ok: true });
}
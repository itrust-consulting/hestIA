import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555'
const ADMIN_USERS_API = API_URL + '/admin/users/user';

export const GET: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const { id } = params;

  const res = await fetch(`${ADMIN_USERS_API}/${id}`, {
    headers: { Authorization: `Bearer ${token}` }
  });

  const body = await res.text();

  return new Response(body, {
    status: res.status,
    headers: { 'content-type': res.headers.get('content-type') ?? 'application/json' }
  });
};

import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555';
const ADMIN_ROLES_API = API_URL + '/admin/roles';

export const GET: RequestHandler = async ({ cookies }) => {
  const token = cookies.get('token');

  const res = await fetch(ADMIN_ROLES_API, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });

  const body = await res.text();

  return new Response(body, {
    status: res.status,
    headers: {
      'content-type': res.headers.get('content-type') ?? 'application/json'
    }
  });
};
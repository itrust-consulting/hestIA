import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555';
const ADMIN_ORGS_API = API_URL + '/admin/organizations';

// List organizations
export const GET: RequestHandler = async ({ cookies }) => {
  const token = cookies.get('token');

  const res = await fetch(ADMIN_ORGS_API, {
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

// Create organization (used by "Add organization")
export const POST: RequestHandler = async ({ request, cookies }) => {
  const token = cookies.get('token');
  const body = await request.text();

  const res = await fetch(ADMIN_ORGS_API + '/create', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body
  });

  const text = await res.text();

  return new Response(text, {
    status: res.status,
    headers: {
      'content-type': res.headers.get('content-type') ?? 'application/json'
    }
  });
};
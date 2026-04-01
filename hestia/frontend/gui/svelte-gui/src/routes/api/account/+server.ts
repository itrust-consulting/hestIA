import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555'
const ACCOUNT_API = API_URL + '/account';

export const GET: RequestHandler = async ({ cookies }) => {
  const token = cookies.get('token');

  const upstream = await fetch(ACCOUNT_API, {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });

  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: { 'content-type': 'application/json' }
  });
};
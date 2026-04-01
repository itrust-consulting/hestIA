import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555'
const ACCOUNT_PW_API = API_URL + '/account/password';

export const PATCH: RequestHandler = async ({ request, cookies }) => {
  const token = cookies.get('token');

  const upstream = await fetch(ACCOUNT_PW_API, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: await request.text()
  });

  return new Response(await upstream.text(), { status: upstream.status });
};
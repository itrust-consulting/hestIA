import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ request, cookies }) => {
  const res = await backendFetch('/admin/auth/settings/test', cookies.get('token'), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: await request.text()
  });
  return proxyResponse(res);
};

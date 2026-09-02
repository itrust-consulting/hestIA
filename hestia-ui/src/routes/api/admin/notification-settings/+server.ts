import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ cookies }) => {
  const res = await backendFetch('/admin/notification-settings', cookies.get('token'));
  return proxyResponse(res);
};

export const PUT: RequestHandler = async ({ request, cookies }) => {
  const res = await backendFetch('/admin/notification-settings', cookies.get('token'), {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: await request.text(),
  });
  return proxyResponse(res);
};

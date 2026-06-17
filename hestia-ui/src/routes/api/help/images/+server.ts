import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch('/help/images', token);
  return proxyResponse(res);
};

export const POST: RequestHandler = async ({ request, cookies }) => {
  const token = cookies.get('token');
  // Forward multipart body verbatim — preserves the boundary in content-type.
  const res = await backendFetch('/help/images', token, {
    method: 'POST',
    headers: { 'content-type': request.headers.get('content-type') ?? '' },
    body: await request.arrayBuffer(),
  });
  return proxyResponse(res);
};

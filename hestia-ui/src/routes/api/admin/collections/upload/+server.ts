import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ request, cookies }) => {
  const token = cookies.get('token');
  // Pass FormData directly — fetch sets multipart Content-Type + boundary automatically
  const formData = await request.formData();
  const res = await backendFetch('/api/upload', token, {
    method: 'POST',
    body: formData,
  });
  return proxyResponse(res);
};

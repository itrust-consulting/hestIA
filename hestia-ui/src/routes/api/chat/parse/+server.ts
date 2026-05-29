import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ request, cookies }) => {
  const token = cookies.get('token');
  try {
    const formData = await request.formData();
    const res = await backendFetch('/api/parse', token, {
      method: 'POST',
      body: formData,
    });
    return proxyResponse(res);
  } catch {
    return Response.json({ error: 'Parse failed' }, { status: 500 });
  }
};

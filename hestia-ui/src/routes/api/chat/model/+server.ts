import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ cookies }) => {
  try {
    const res = await backendFetch('/api/chat/model', cookies.get('token'));
    return proxyResponse(res);
  } catch {
    return Response.json({ error: 'Failed to fetch active model' }, { status: 500 });
  }
};

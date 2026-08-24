import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ params, cookies }) => {
  const res = await backendFetch(`/admin/llm/connections/${params.id}/activate`, cookies.get('token'), { method: 'POST' });
  return proxyResponse(res);
};

import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const DELETE: RequestHandler = async ({ params, url, cookies }) => {
  const token = cookies.get('token');
  const sourceUri = url.searchParams.get('source_uri') ?? '';
  const backendUrl = `/api/collections/${encodeURIComponent(params.name)}/documents?source_uri=${encodeURIComponent(sourceUri)}`;
  const res = await backendFetch(backendUrl, token, { method: 'DELETE' });
  return proxyResponse(res);
};

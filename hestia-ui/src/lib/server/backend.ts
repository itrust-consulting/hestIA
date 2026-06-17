import { env } from '$env/dynamic/private';

const BASE_URL = env.PRIVATE_MICROSERVICE_URL || 'http://localhost:5555';

export function backendFetch(
  path: string,
  token: string | undefined,
  init: RequestInit = {}
): Promise<Response> {
  return fetch(BASE_URL + path, {
    ...init,
    headers: {
      ...(init.headers as Record<string, string>),
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });
}

export async function proxyBinaryResponse(upstream: Response): Promise<Response> {
  if (!upstream.ok) {
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: { 'content-type': 'application/json' }
    });
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/octet-stream' }
  });
}

export async function proxyResponse(upstream: Response): Promise<Response> {
  const body = await upstream.text();
  if (upstream.status >= 500) {
    console.error(`Backend error ${upstream.status}:`, body);
    return new Response(JSON.stringify({ detail: 'An internal error occurred.' }), {
      status: upstream.status,
      headers: { 'content-type': 'application/json' }
    });
  }
  return new Response(body, {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
  });
}

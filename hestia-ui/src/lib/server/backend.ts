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
  const headers: Record<string, string> = {
    'content-type': upstream.headers.get('content-type') ?? 'application/octet-stream'
  };
  const disposition = upstream.headers.get('content-disposition');
  if (disposition) headers['content-disposition'] = disposition;
  return new Response(upstream.body, { status: upstream.status, headers });
}

// FastAPI's default validation handler puts a *list* of structured error
// objects ({loc, msg, type, input}) in `detail` for a 422, unlike every
// other backend error handler (which puts a plain string there). Every
// frontend form that surfaces `detail` in a toast assumes it's already
// display-ready text, so a raw validation error would otherwise render as
// "[object Object]" -- flatten it here, once, instead of in every caller.
function flattenValidationDetail(rawBody: string): string | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawBody);
  } catch {
    return null;
  }
  if (typeof parsed !== 'object' || parsed === null || !('detail' in parsed)) return null;
  const detail = (parsed as { detail: unknown }).detail;
  if (!Array.isArray(detail)) return null;

  return detail
    .map((entry) => {
      if (entry && typeof entry === 'object' && 'msg' in entry) {
        const loc = Array.isArray((entry as { loc?: unknown }).loc)
          ? (entry as { loc: unknown[] }).loc.join('.')
          : '';
        const msg = (entry as { msg: unknown }).msg;
        return loc ? `${loc}: ${msg}` : String(msg);
      }
      return typeof entry === 'string' ? entry : JSON.stringify(entry);
    })
    .join('; ');
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
  if (upstream.status >= 400) {
    const flattened = flattenValidationDetail(body);
    if (flattened !== null) {
      return new Response(JSON.stringify({ detail: flattened }), {
        status: upstream.status,
        headers: { 'content-type': 'application/json' }
      });
    }
  }
  return new Response(body, {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
  });
}

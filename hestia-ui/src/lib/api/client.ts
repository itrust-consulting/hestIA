import { goto } from '$app/navigation';

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const hasBody = init.body !== undefined;
  const res = await fetch(path, {
    ...init,
    headers: {
      ...(hasBody ? { 'content-type': 'application/json' } : {}),
      ...(init.headers as Record<string, string>)
    }
  });

  if (res.status === 401) {
    goto('/login');
    throw new ApiError(401, 'Session expired');
  }

  return res;
}

export const api = {
  get: (path: string) =>
    request(path),

  post: (path: string, body: unknown) =>
    request(path, { method: 'POST', body: JSON.stringify(body) }),

  patch: (path: string, body: unknown) =>
    request(path, { method: 'PATCH', body: JSON.stringify(body) }),

  delete: (path: string) =>
    request(path, { method: 'DELETE' }),

  stream: (path: string, body: unknown, signal?: AbortSignal) =>
    request(path, { method: 'POST', body: JSON.stringify(body), signal })
};

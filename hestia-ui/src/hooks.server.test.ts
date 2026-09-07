import { describe, expect, it, vi, beforeEach } from 'vitest';
import * as backend from '$lib/server/backend';

vi.mock('$lib/server/backend', () => ({ backendFetch: vi.fn() }));

import { handle } from './hooks.server';

const backendFetch = vi.mocked(backend.backendFetch);

function makeEvent(opts: { token?: string; pathname?: string; search?: string } = {}) {
  const { token, pathname = '/chat', search = '' } = opts;
  const cookies = {
    get: vi.fn(() => token),
    delete: vi.fn(),
  };
  const locals: any = {};
  const url = new URL(`http://localhost${pathname}${search}`);
  const event = { cookies, locals, url } as any;
  return { event, cookies, locals };
}

describe('hooks.server handle', () => {
  beforeEach(() => {
    backendFetch.mockReset();
  });

  it('leaves locals.user null and never calls backendFetch when there is no token cookie', async () => {
    const { event, locals } = makeEvent();
    const resolve = vi.fn(async () => new Response('ok'));

    const response = await handle({ event, resolve } as any);

    expect(backendFetch).not.toHaveBeenCalled();
    expect(locals.user).toBeNull();
    expect(resolve).toHaveBeenCalledOnce();
    expect(response.headers.get('X-Content-Type-Options')).toBe('nosniff');
    expect(response.headers.get('X-Frame-Options')).toBe('DENY');
  });

  it('sets locals.user from the backend profile when the token is valid', async () => {
    const { event, locals } = makeEvent({ token: 'good-token' });
    backendFetch.mockResolvedValue({ ok: true, json: async () => ({ id: 'u1', permissions: {} }) } as Response);
    const resolve = vi.fn(async () => new Response('ok'));

    await handle({ event, resolve } as any);

    expect(backendFetch).toHaveBeenCalledWith('/account', 'good-token');
    expect(locals.user).toEqual({ id: 'u1', permissions: {} });
  });

  it('deletes the cookie and leaves locals.user null when the backend rejects the token', async () => {
    const { event, locals, cookies } = makeEvent({ token: 'stale-token' });
    backendFetch.mockResolvedValue({ ok: false } as Response);
    const resolve = vi.fn(async () => new Response('ok'));

    await handle({ event, resolve } as any);

    expect(cookies.delete).toHaveBeenCalledWith('token', { path: '/' });
    expect(locals.user).toBeNull();
  });

  it('swallows a backendFetch failure and still resolves the request', async () => {
    const { event, locals } = makeEvent({ token: 'x' });
    backendFetch.mockRejectedValue(new Error('network down'));
    const resolve = vi.fn(async () => new Response('ok'));
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    const response = await handle({ event, resolve } as any);

    expect(locals.user).toBeNull();
    expect(resolve).toHaveBeenCalledOnce();
    expect(response.status).toBe(200);
    consoleError.mockRestore();
  });

  it('redirects /mod/* to /admin/*, preserving the query string, without resolving', async () => {
    const { event } = makeEvent({ pathname: '/mod/tenants', search: '?tab=members' });
    const resolve = vi.fn(async () => new Response('ok'));

    const response = await handle({ event, resolve } as any);

    expect(response.status).toBe(301);
    expect(response.headers.get('location')).toBe('http://localhost/admin/tenants?tab=members');
    expect(resolve).not.toHaveBeenCalled();
  });

  it('redirects the exact /mod path too', async () => {
    const { event } = makeEvent({ pathname: '/mod' });
    const resolve = vi.fn(async () => new Response('ok'));

    const response = await handle({ event, resolve } as any);

    expect(response.status).toBe(301);
    expect(response.headers.get('location')).toBe('http://localhost/admin');
  });

  describe('/api/admin/* guard', () => {
    it('returns 403 when there is no token (no user)', async () => {
      const { event } = makeEvent({ pathname: '/api/admin/users' });
      const resolve = vi.fn(async () => new Response('ok'));

      const response = await handle({ event, resolve } as any);

      expect(response.status).toBe(403);
      expect(await response.json()).toEqual({ detail: 'Forbidden' });
      expect(resolve).not.toHaveBeenCalled();
    });

    it('returns 403 for a user with neither admin nor moderator permissions', async () => {
      const { event } = makeEvent({ pathname: '/api/admin/users', token: 'tok' });
      backendFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ permissions: { is_admin: false, moderated_tenants: [] } }),
      } as Response);
      const resolve = vi.fn(async () => new Response('ok'));

      const response = await handle({ event, resolve } as any);

      expect(response.status).toBe(403);
      expect(resolve).not.toHaveBeenCalled();
    });

    it('passes through for an admin', async () => {
      const { event } = makeEvent({ pathname: '/api/admin/users', token: 'tok' });
      backendFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ permissions: { is_admin: true, moderated_tenants: [] } }),
      } as Response);
      const resolve = vi.fn(async () => new Response('ok'));

      const response = await handle({ event, resolve } as any);

      expect(resolve).toHaveBeenCalledOnce();
      expect(response.status).toBe(200);
    });

    it('passes through for a tenant moderator', async () => {
      const { event } = makeEvent({ pathname: '/api/admin/tenants', token: 'tok' });
      backendFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ permissions: { is_admin: false, moderated_tenants: [1] } }),
      } as Response);
      const resolve = vi.fn(async () => new Response('ok'));

      const response = await handle({ event, resolve } as any);

      expect(resolve).toHaveBeenCalledOnce();
      expect(response.status).toBe(200);
    });
  });
});

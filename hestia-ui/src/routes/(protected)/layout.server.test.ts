import { describe, expect, it } from 'vitest';
import { isRedirect } from '@sveltejs/kit';
import { load } from './+layout.server';

describe('(protected)/+layout.server load', () => {
  it('redirects to /login when there is no user', () => {
    let caught: unknown;
    try {
      load({ locals: { user: null } } as any);
    } catch (e) {
      caught = e;
    }

    expect(isRedirect(caught)).toBe(true);
    expect((caught as any).status).toBe(302);
    expect((caught as any).location).toBe('/login');
  });

  it('returns an empty object without redirecting when a user is present', () => {
    const result = load({ locals: { user: { id: 'u1' } } } as any);
    expect(result).toEqual({});
  });
});

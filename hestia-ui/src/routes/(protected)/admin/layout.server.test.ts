import { describe, expect, it } from 'vitest';
import { isHttpError } from '@sveltejs/kit';
import { load } from './+layout.server';

describe('(protected)/admin/+layout.server load', () => {
  it('rejects with 403 when there is no user', () => {
    let caught: unknown;
    try {
      load({ locals: { user: null } } as any);
    } catch (e) {
      caught = e;
    }

    expect(isHttpError(caught)).toBe(true);
    expect((caught as any).status).toBe(403);
  });

  it('rejects with 403 for a user who is neither admin nor a tenant moderator', () => {
    let caught: unknown;
    try {
      load({ locals: { user: { permissions: { is_admin: false, moderated_tenants: [] } } } } as any);
    } catch (e) {
      caught = e;
    }

    expect(isHttpError(caught)).toBe(true);
    expect((caught as any).status).toBe(403);
  });

  it('passes for an admin and reports isAdmin true', () => {
    const result = load({
      locals: { user: { permissions: { is_admin: true, moderated_tenants: [] }, orgs: [] } },
    } as any);

    expect(result.isAdmin).toBe(true);
    expect(result.moderated_tenants).toEqual([]);
  });

  it('passes for a tenant moderator even without the admin flag', () => {
    const result = load({
      locals: { user: { permissions: { is_admin: false, moderated_tenants: [7] }, orgs: [] } },
    } as any);

    expect(result.isAdmin).toBe(false);
    expect(result.moderated_tenants).toEqual([7]);
  });

  it('maps user_orgs from locals.user.orgs', () => {
    const orgs = [{ id: 1, name: 'Acme', abbr: 'AC' }];
    const result = load({
      locals: { user: { permissions: { is_admin: true, moderated_tenants: [] }, orgs } },
    } as any);

    expect(result.user_orgs).toEqual(orgs);
  });

  it('defaults user_orgs to an empty array when locals.user.orgs is absent', () => {
    const result = load({
      locals: { user: { permissions: { is_admin: true, moderated_tenants: [] } } },
    } as any);

    expect(result.user_orgs).toEqual([]);
  });
});

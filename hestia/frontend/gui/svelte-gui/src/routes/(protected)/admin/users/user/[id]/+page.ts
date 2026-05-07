import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ fetch, params }) => {
  const res = await fetch(`/api/admin/users/user/${params.id}`);

  if (!res.ok) {
    throw error(res.status, 'Failed to load user');
  }

  const user = await res.json();

  return {
    user
  };
};
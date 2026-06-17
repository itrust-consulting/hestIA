export async function load({ url, fetch }) {
  const section = url.searchParams.get('section') ?? 'profile';
  const res = await fetch('/api/account');
  const user = res.ok ? await res.json() : null;
  return { section, user };
}

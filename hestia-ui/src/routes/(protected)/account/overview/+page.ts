export async function load({ url, fetch }) {
  const section = url.searchParams.get('section') ?? 'profile';
  const res = await fetch('/api/account');
  const user = res.ok ? await res.json() : null;

  if (section !== 'tenants') {
    return { section, user };
  }

  const [orgsRes, requestsRes, invitationsRes] = await Promise.all([
    fetch('/api/organizations/browse'),
    fetch('/api/account/join-requests'),
    fetch('/api/account/invitations?status=pending'),
  ]);
  const organizations = orgsRes.ok ? ((await orgsRes.json()).organizations ?? []) : [];
  const joinRequests = requestsRes.ok ? ((await requestsRes.json()).requests ?? []) : [];
  const invitations = invitationsRes.ok ? ((await invitationsRes.json()).invitations ?? []) : [];

  return { section, user, organizations, joinRequests, invitations };
}

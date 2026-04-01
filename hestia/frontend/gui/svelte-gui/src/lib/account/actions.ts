export async function getAccountDetails() {
  const res = await fetch('/api/account', {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    throw new Error(`Failed to load account info: ${res.status}`);
  }

  return await res.json();
}


export async function changePassword(current: string, next: string) {
    const res = await fetch('/api/account/password', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            current_pw: current,
            new_pw: next
        })
    });

    if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? 'Password update failed.');
    }

    return await res.json();
}

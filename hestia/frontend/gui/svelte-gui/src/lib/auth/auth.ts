export function isTokenExpired(token: string): boolean {
    try {
        const [, payloadB64] = token.split('.');
        const payloadJson = atob(payloadB64);
        const payload = JSON.parse(payloadJson);

        if (!payload.exp) return true;

        const nowSeconds = Math.floor(Date.now() / 1000);
        return payload.exp < nowSeconds;
    } catch {
        return true; // malformed token => treat as expired
    }
}


export async function login(username: string, password: string) {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password })
  });

  return await res.json();
}
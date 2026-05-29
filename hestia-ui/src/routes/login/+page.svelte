<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import { login } from '$lib/auth/auth';
  import { scheduleTokenExpiration } from '$lib/auth/session';
  import { env } from '$env/dynamic/public';

  const isOidc = env.PUBLIC_AUTH_MODE === 'oidc';

  let username = $state('');
  let password = $state('');
  let error = $state<string | null>(null);
  let loading = $state(false);
  let showLocalForm = $state(!isOidc);

  const expiredParam = $derived(page.url.searchParams.get('expired'));
  const errorParam = $derived(page.url.searchParams.get('error'));

  const OIDC_ERRORS: Record<string, string> = {
    oidc_unavailable:      'SSO service is unavailable. Try again or use a local account.',
    oidc_no_code:          'SSO login was cancelled or failed.',
    oidc_state_mismatch:   'SSO session expired. Please try again.',
    oidc_exchange_failed:  'SSO token exchange failed. Try again or contact your administrator.',
  };

  $effect(() => {
    if (expiredParam === '1') error = 'Session expired. Please log in again.';
    else if (errorParam)      error = OIDC_ERRORS[errorParam] ?? 'An authentication error occurred.';
  });

  async function handleSubmit() {
    error = null;

    if (!username || !password) {
      error = 'Username and password are required.';
      return;
    }

    loading = true;
    const res = await login(username, password);
    loading = false;

    if (res.ok) {
      scheduleTokenExpiration(res.exp);
      await invalidateAll();
      if (res.must_change_pw) {
        goto('/account/overview?section=security');
      } else {
        goto('/chat');
      }
    } else {
      error = res.error ?? 'Login failed.';
    }
  }
</script>

<div class="login-container">
  <div class="login-card">
    <h1 class="login-title">Welcome to hestIA</h1>

    {#if error}
      <div class="login-error">{error}</div>
    {/if}

    {#if isOidc}
      <a href="/api/login/oidc" class="login-button sso-button" data-sveltekit-reload>
        Log in with SSO
      </a>

      <button
        class="local-toggle"
        onclick={() => (showLocalForm = !showLocalForm)}
      >
        {showLocalForm ? 'Hide local login' : 'Use local account'}
      </button>
    {/if}

    {#if showLocalForm}
      {#if isOidc}
        <div class="divider"><span>Local account</span></div>
      {/if}

      <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="login-form">
        <input
          type="text"
          placeholder="Username"
          bind:value={username}
          class="login-input"
          autocomplete="username"
        />

        <input
          type="password"
          placeholder="Password"
          bind:value={password}
          class="login-input"
          autocomplete="current-password"
          required
        />

        <button
          type="submit"
          class="login-button"
          disabled={loading}
        >
          {loading ? 'Logging in…' : 'Log In'}
        </button>
      </form>
    {/if}
  </div>
</div>

<style>
  .login-container {
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: var(--color-neutral-100);
    padding: 2rem;
  }

  .login-card {
    background: var(--color-neutral-50);
    padding: 2rem;
    border-radius: var(--radius-2xl);
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    width: 360px;
    max-width: 90%;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .login-title {
    font-size: var(--text-2xl);
    font-weight: 700;
    text-align: center;
    margin-bottom: .25rem;
  }

  .login-subtitle {
    text-align: center;
    color: var(--color-neutral-600);
    margin-bottom: 1rem;
  }

  .login-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .login-input {
    padding: .75rem 1rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-neutral-300);
    font-size: var(--text-base);
    width: 100%;
  }

  .login-input:focus {
    border-color: var(--color-blue-600);
    outline: none;
    box-shadow: 0 0 0 3px color-mix(in oklab,var(--color-blue-600) 20%,transparent);
  }

  .login-button {
    padding: .75rem 1rem;
    border-radius: var(--radius-lg);
    background: var(--color-blue-600);
    color: white;
    font-size: var(--text-base);
    font-weight: 600;
    cursor: pointer;
    transition: background-color .15s ease;
  }

  .login-button:hover:not(:disabled) {
    background: var(--color-blue-700);
  }

  .login-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .login-error {
    background: var(--color-red-100);
    color: var(--color-red-700);
    padding: .75rem;
    border-radius: var(--radius-lg);
    font-size: var(--text-sm);
    text-align: center;
  }

  .sso-button {
    display: block;
    text-align: center;
    text-decoration: none;
  }

  .local-toggle {
    background: none;
    border: none;
    color: var(--color-neutral-500);
    font-size: var(--text-sm);
    cursor: pointer;
    text-align: center;
    padding: 0;
  }

  .local-toggle:hover {
    color: var(--color-neutral-700);
    text-decoration: underline;
  }

  .divider {
    display: flex;
    align-items: center;
    gap: .75rem;
    color: var(--color-neutral-400);
    font-size: var(--text-sm);
  }

  .divider::before,
  .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--color-neutral-200);
  }
</style>
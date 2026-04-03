<script lang="ts">
  import { redirect } from '@sveltejs/kit';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { login } from '$lib/auth/auth';
  import { scheduleTokenExpiration } from '$lib/auth/session'


  let username = $state('');
  let password = $state('');
  let error = $state<string | null>(null);
  let loading = $state(false);
  
  const expiredParam = $derived(page.url.searchParams.get('expired'));

  $effect(() => {
    if (expiredParam === '1') {
      error = "Session expired. Please log in again.";
    }
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
      
      if (res.must_change_pw) {
        goto('/account/overview?section=security');
      }
      else {
        goto('/chat');
      }
    } 
    else {
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

    <form on:submit|preventDefault={handleSubmit} class="login-form">
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
    background: white;
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
</style>
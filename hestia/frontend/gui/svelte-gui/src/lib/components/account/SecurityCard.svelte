<script lang="ts">
  import { changePassword } from '$lib/account/actions';
  import ShowIcon from '../icons/showIcon.svelte';
  import HideIcon from '../icons/hideIcon.svelte';

  export let mustChangePw: boolean = false;

  let currentPassword = '';
  let newPassword = '';
  let confirmPassword = '';

  let showCurrent = false;
  let showNew = false;
  let showConfirm = false;

  let error: string | null = null;
  let success: string | null = null;
  let loading = false;

  if (mustChangePw) {
    error = "Please change the default password."
  }

  const rules = {
    length: (pw: string) => pw.length >= 10,
    lower: (pw: string) => /[a-z]/.test(pw),
    upper: (pw: string) => /[A-Z]/.test(pw),
    number: (pw: string) => /\d/.test(pw),
    special: (pw: string) => /[^A-Za-z0-9]/.test(pw)
  };

  function validateNewPassword() {
    return Object.values(rules).every(fn => fn(newPassword));
  }

  function getStrength(pw: string) {
    let score = 0;
    if (rules.length(pw)) score++;
    if (rules.lower(pw)) score++;
    if (rules.upper(pw)) score++;
    if (rules.number(pw)) score++;
    if (rules.special(pw)) score++;

    if (score <= 1) return { label: "Very Weak", level: 1 };
    if (score === 2) return { label: "Weak", level: 2 };
    if (score === 3) return { label: "Medium", level: 3 };
    if (score === 4) return { label: "Strong", level: 4 };
    return { label: "Very Strong", level: 5 };
  }

  $: strength = getStrength(newPassword);

  async function handleChangePassword() {
    error = null;
    success = null;

    if (!currentPassword || !newPassword || !confirmPassword) {
      error = "All fields are required.";
      return;
    }

    if (newPassword !== confirmPassword) {
      error = "New passwords do not match.";
      return;
    }

    if (newPassword === currentPassword) {
      error = "New password cannot be the same as the current password.";
      return;
    }

    if (!validateNewPassword()) {
      error = "New password does not meet security requirements.";
      return;
    }

    loading = true;

    try {
      await changePassword(currentPassword, newPassword);
      success = "Password has been changed.";

      currentPassword = "";
      newPassword = "";
      confirmPassword = "";
    } catch (e: any) {
      error = e.message ?? "Failed to change password.";
    } finally {
      loading = false;
    }
  }
</script>

<h1 class="section-title">Security Settings</h1>

<div class="security-card">
  <div class="security-section">
    <h2>Password</h2>
    <p class="desc">Update your account password to keep your profile secure.</p>

    {#if error}
      <div class="error-box">{error}</div>
    {/if}

    {#if success}
      <div class="success-box">{success}</div>
    {/if}



    <form class="form" on:submit|preventDefault={handleChangePassword}>

      <!-- Current Password -->
      <div class="form-group">
        <label>Current Password</label>
        <div class="input-wrap">
          <input
            type={showCurrent ? "text" : "password"}
            bind:value={currentPassword}
            required
          />
          <button type="button" class="show-btn" on:click={() => showCurrent = !showCurrent}>
            {#if showCurrent}
                <HideIcon />
            {:else}
                <ShowIcon />
            {/if}
          </button>
        </div>
      </div>

      <!-- New Password -->
      <div class="form-group">
        <label>New Password</label>
        <div class="input-wrap">
          <input
            type={showNew ? "text" : "password"}
            bind:value={newPassword}
            required
          />
          <button type="button" class="show-btn" on:click={() => showNew = !showNew}>
            {#if showNew}
                <HideIcon />
            {:else}
                <ShowIcon />
            {/if}
          </button>
        </div>
      </div>

      <!-- Confirm Password -->
      <div class="form-group">
        <label>Confirm New Password</label>
        <div class="input-wrap">
          <input
            type={showConfirm ? "text" : "password"}
            bind:value={confirmPassword}
            required
          />
          <button type="button" class="show-btn" on:click={() => showConfirm = !showConfirm}>
            {#if showConfirm}
                <HideIcon />
            {:else}
                <ShowIcon />
            {/if}
          </button>
        </div>
      </div>
          <!-- ONLY SHOW WHEN USER TYPES -->
        {#if newPassword.length > 0}
        <div class="requirements">
            <p>Password must contain:</p>
            <ul>
            <li class:valid={rules.length(newPassword)}>✔ At least 10 characters</li>
            <li class:valid={rules.lower(newPassword)}>✔ Lowercase letter</li>
            <li class:valid={rules.upper(newPassword)}>✔ Uppercase letter</li>
            <li class:valid={rules.number(newPassword)}>✔ Number</li>
            <li class:valid={rules.special(newPassword)}>✔ Special character</li>
            </ul>

            <!-- Strength Meter -->
            <div class="strength">
            <div class="bar-container">
                {#each Array(5) as _, i}
                <div class="bar {strength.level > i ? 'active' : ''}"></div>
                {/each}
            </div>
            <span class="strength-label">{strength.label}</span>
            </div>
        </div>
        {/if}
      <button type="submit" class="btn dark" disabled={loading}>
        {loading ? "Saving…" : "Change Password"}
      </button>
    </form>
  </div>
</div>

<style>
  .section-title {
    font-size: var(--text-xl);
    font-weight: 700;
    margin-bottom: 1.5rem;
  }

  .security-card {
    background: white;
    padding: 1.75rem;
    border-radius: var(--radius-2xl);
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .security-section h2 {
    font-size: var(--text-lg);
    font-weight: 700;
  }

  .desc {
    font-size: var(--text-sm);
    padding: .25rem;
  }

  .error-box {
    color: var(--color-red-700);
  }

  .success-box {
    color: var(--color-green-600)
  }

  .requirements {
    background: var(--color-neutral-100);
    padding: 1rem;
    border-radius: var(--radius-lg);
    font-size: var(--text-sm);
    margin-bottom: 1rem;
  }

  .requirements ul {
    padding-left: 1.25rem;
    margin-top: 0.5rem;
  }

  .requirements li {
    color: var(--color-neutral-700);
    margin-bottom: 0.35rem;
  }

  .requirements li.valid {
    color: var(--color-green-700);
    font-weight: 600;
  }

  .strength {
    margin-top: 1rem;
    display: flex;
    align-items: center;
    gap: .75rem;
  }

  .bar-container {
    display: flex;
    gap: 4px;
  }

  .bar {
    width: 28px;
    height: 6px;
    background: var(--color-neutral-300);
    border-radius: 4px;
    transition: background 200ms ease;
  }

  .bar.active:nth-child(1) { background: #ef4444; }
  .bar.active:nth-child(2) { background: #f59e0b; }
  .bar.active:nth-child(3) { background: #fbbf24; }
  .bar.active:nth-child(4) { background: #84cc16; }
  .bar.active:nth-child(5) { background: #22c55e; }

  .strength-label {
    font-size: var(--text-sm);
    color: var(--color-neutral-700);
    font-weight: 600;
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: .35rem;
  }

  label {
    font-size: var(--text-xs);
    text-transform: uppercase;
    color: var(--color-neutral-600);
    padding-top: .25rem;
  }

  .input-wrap {
    display: flex;
    align-items: center;
    position: relative;
  }

  input {
    width: 100%;
    padding: .65rem .85rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-neutral-300);
    font-size: var(--text-base);
  }

  .show-btn {
    position: absolute;
    right: .75rem;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1rem;
    opacity: 0.6;
  }

  .show-btn:hover {
    opacity: 1;
  }

  .btn {
    padding: .65rem 1.25rem;
    border-radius: var(--radius-lg);
    font-weight: 600;
    cursor: pointer;
    border: none;
    width: fit-content;
  }

  .btn.dark {
    background: var(--color-blue-600);
    color: white;
  }

  .btn.dark:hover:not(:disabled) {
    background: var(--color-blue-700);
  }
</style>
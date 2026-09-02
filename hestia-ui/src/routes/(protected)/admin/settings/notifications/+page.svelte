<script lang="ts">
  import { invalidateAll } from '$app/navigation';
  import { addToast } from '$lib/stores/toast';
  import type { WelcomeSettings, Broadcast } from '$lib/types';

  const { data }: { data: { welcomeSettings: WelcomeSettings; broadcasts: Broadcast[] } } = $props();

  // ── Welcome message ──────────────────────────────────────────────────────
  let welcomeTitle = $state(data.welcomeSettings.welcome_title);
  let welcomeBody = $state(data.welcomeSettings.welcome_body);
  let welcomePhase = $state<'saving' | null>(null);
  let welcomeError = $state<string | null>(null);

  async function saveWelcome() {
    welcomeError = null;
    welcomePhase = 'saving';
    try {
      const res = await fetch('/api/admin/notification-settings', {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ welcome_title: welcomeTitle, welcome_body: welcomeBody }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Welcome message updated.', 'success');
    } catch (e: any) {
      welcomeError = e.message ?? 'Failed to save.';
    } finally {
      welcomePhase = null;
    }
  }

  // ── Send broadcast ───────────────────────────────────────────────────────
  let broadcastTitle = $state('');
  let broadcastBody = $state('');
  let broadcastLink = $state('');
  let broadcastPhase = $state<'sending' | null>(null);
  let broadcastError = $state<string | null>(null);

  async function sendBroadcast() {
    if (!broadcastTitle.trim()) return;
    broadcastError = null;
    broadcastPhase = 'sending';
    try {
      const res = await fetch('/api/admin/notifications/broadcast', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          title: broadcastTitle.trim(),
          body: broadcastBody.trim() || null,
          link: broadcastLink.trim() || null,
        }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Notification broadcast to all users.', 'success');
      broadcastTitle = '';
      broadcastBody = '';
      broadcastLink = '';
      await invalidateAll();
    } catch (e: any) {
      broadcastError = e.message ?? 'Failed to broadcast.';
    } finally {
      broadcastPhase = null;
    }
  }

  const formatDateTime = (ts: number) =>
    ts ? new Date(ts).toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';

  function truncate(s: string, n = 80): string {
    return s.length > n ? `${s.slice(0, n)}…` : s;
  }
</script>

<div class="admin-content">
  <h1 class="title">Notifications</h1>

  <div class="section-header"><h3>Welcome Message</h3></div>
  <div class="panel">
    <div class="form-stack">
      <label class="field">
        <span>Title</span>
        <input type="text" bind:value={welcomeTitle} />
      </label>
      <label class="field">
        <span>Body <span class="hint">— supports markdown, shown to every new user's account</span></span>
        <textarea rows="6" bind:value={welcomeBody}></textarea>
      </label>
      {#if welcomeError}<div class="field-error">{welcomeError}</div>{/if}
      <div>
        <button class="action-btn" onclick={saveWelcome} disabled={welcomePhase !== null}>
          {welcomePhase === 'saving' ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  </div>

  <div class="section-header"><h3>Send Broadcast</h3></div>
  <div class="panel">
    <div class="form-stack">
      <label class="field">
        <span>Title</span>
        <input type="text" bind:value={broadcastTitle} placeholder="e.g. New version deployed" />
      </label>
      <label class="field">
        <span>Body <span class="hint">— optional, supports markdown</span></span>
        <textarea rows="4" bind:value={broadcastBody}></textarea>
      </label>
      <label class="field">
        <span>Link <span class="hint">— optional</span></span>
        <input type="text" bind:value={broadcastLink} placeholder="/chat" />
      </label>
      {#if broadcastError}<div class="field-error">{broadcastError}</div>{/if}
      <div>
        <button class="action-btn" onclick={sendBroadcast} disabled={broadcastPhase !== null || !broadcastTitle.trim()}>
          {broadcastPhase === 'sending' ? 'Sending…' : 'Broadcast'}
        </button>
      </div>
    </div>
  </div>

  <div class="section-header"><h3>History</h3></div>
  <div class="panel">
    {#if data.broadcasts.length === 0}
      <p class="empty-note">No broadcasts sent yet.</p>
    {:else}
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Body</th>
              <th>Link</th>
              <th>Sent</th>
            </tr>
          </thead>
          <tbody>
            {#each data.broadcasts as b}
              <tr>
                <td class="name">{b.title}</td>
                <td class="muted" title={b.body ?? ''}>{b.body ? truncate(b.body) : '—'}</td>
                <td class="muted mono">{b.link ?? '—'}</td>
                <td class="muted">{formatDateTime(b.created_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

<style>
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-6xl);
  margin-inline: auto;
}

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 1rem;
}

.section-header { margin: 1.5rem 0 0.75rem; }
.section-header:first-of-type { margin-top: 0; }
.section-header h3 {
  font-size: var(--text-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-neutral-600);
}

.panel {
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.form-stack { display: flex; flex-direction: column; gap: 0.875rem; }

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
}
.field input, .field textarea {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
  font-family: inherit;
  width: 100%;
  resize: vertical;
}
.field input:focus, .field textarea:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}

.hint { font-weight: 400; color: var(--color-neutral-400); font-size: var(--text-xs); }

.field-error {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
}

.action-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.empty-note {
  color: var(--color-neutral-500);
  font-size: var(--text-sm);
}

.table-container {
  background: var(--color-white);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-lg);
  max-height: 28rem;
  overflow-y: auto;
}

.data-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.data-table thead th {
  position: sticky; top: 0;
  background: var(--color-neutral-100);
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-neutral-500);
}
.data-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-200);
  vertical-align: top;
}
.data-table tbody tr:last-child td { border-bottom: none; }

.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: var(--text-xs); }
.muted { color: var(--color-neutral-500); }
.name { font-weight: 500; }
</style>

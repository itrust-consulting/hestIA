<script lang="ts">
  import InfoIcon    from '$lib/components/icons/infoIcon.svelte';
  import ChatIcon    from '$lib/components/icons/chaticon.svelte';
  import BookIcon    from '$lib/components/icons/bookIcon.svelte';
  import AdminIcon   from '$lib/components/icons/adminIcon.svelte';
  import HelpIcon    from '$lib/components/icons/helpIcon.svelte';
  import { version as currentVersion } from '$app/environment';

  export let sections: Array<{ id: string; title: string }> = [];
  export let currentSection: string = 'getting-started';
  export let isAdmin: boolean = false;
  export let onCreate: (title: string) => Promise<void> = async () => {};

  const ICON_MAP: Record<string, any> = {
    'getting-started': InfoIcon,
    'chat':            ChatIcon,
    'documents':       BookIcon,
    'administration':  AdminIcon,
    'faq':             HelpIcon,
  };

  let creating = false;
  let newTitle  = '';
  let creating_pending = false;

  function startCreate() {
    creating  = true;
    newTitle  = '';
  }

  function cancelCreate() {
    creating = false;
    newTitle  = '';
  }

  async function confirmCreate() {
    const title = newTitle.trim();
    if (!title || creating_pending) return;
    creating_pending = true;
    try {
      await onCreate(title);
      creating = false;
      newTitle  = '';
    } finally {
      creating_pending = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter')  { e.preventDefault(); confirmCreate(); }
    if (e.key === 'Escape') { cancelCreate(); }
  }

  function slugPreview(title: string): string {
    return title.toLowerCase().replace(/[^a-z0-9\s-]/g, '').trim().replace(/\s+/g, '-').replace(/-+/g, '-') || '…';
  }
</script>

<aside class="sidebar">
  <div class="sidebar-list">
    {#each sections as s}
      {@const Icon = ICON_MAP[s.id] ?? BookIcon}
      <a
        href="/help?section={s.id}"
        class="sidebar-item"
        class:active={currentSection === s.id}
      >
        <div class="icon-wrapper"><Icon /></div>
        <span class="sidebar-label">{s.title}</span>
      </a>
    {/each}

    {#if isAdmin}
      {#if creating}
        <div class="new-page-form">
          <input
            class="new-page-input"
            type="text"
            bind:value={newTitle}
            placeholder="Page title…"
            onkeydown={handleKeydown}
            autofocus
          />
          {#if newTitle.trim()}
            <span class="slug-hint">/{slugPreview(newTitle)}</span>
          {/if}
          <div class="new-page-actions">
            <button class="new-page-confirm" onclick={confirmCreate} disabled={creating_pending || !newTitle.trim()}>
              {creating_pending ? '…' : '✓'}
            </button>
            <button class="new-page-cancel" onclick={cancelCreate}>✕</button>
          </div>
        </div>
      {:else}
        <button class="new-page-btn" onclick={startCreate}>+ New page</button>
      {/if}
    {/if}
  </div>

  <div class="sidebar-footer">
    <span class="version">{currentVersion}</span>
  </div>
</aside>

<style>
  .sidebar {
    position: sticky;
    top: var(--header-height);
    height: calc(100vh - var(--header-height));
    width: var(--sidebar-width);
    flex-shrink: 0;
    overflow-y: auto;
    border-right: 1px solid var(--color-neutral-200);
    background: var(--color-neutral-200);
    padding: 1rem;
    display: flex;
    flex-direction: column;
  }

  .sidebar-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .sidebar-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    height: 1.75rem;
    padding: 0 0.75rem;
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--color-neutral-700);
    text-decoration: none;
    transition: background-color 120ms ease, color 120ms ease;
    cursor: pointer;
  }

  .sidebar-item:hover {
    background: var(--color-white);
    color: var(--color-neutral-900);
  }

  .sidebar-item.active {
    background: var(--color-white);
    color: var(--color-neutral-900);
    font-weight: 600;
  }

  /* ── New page ─────────────────────────────────────── */

  .new-page-btn {
    margin-top: 0.5rem;
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0 0.75rem;
    height: 1.75rem;
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--color-neutral-500);
    background: transparent;
    border: 1px dashed var(--color-neutral-400);
    cursor: pointer;
    transition: background-color 120ms ease, color 120ms ease, border-color 120ms ease;
  }

  .new-page-btn:hover {
    background: var(--color-white);
    color: var(--color-neutral-700);
    border-color: var(--color-neutral-500);
  }

  .new-page-form {
    margin-top: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .new-page-input {
    width: 100%;
    padding: 0.25rem 0.5rem;
    font-size: var(--text-sm);
    border: 1px solid var(--color-neutral-400);
    border-radius: var(--radius-md);
    background: var(--color-white);
    color: var(--color-neutral-900);
    outline: none;
  }

  .new-page-input:focus {
    border-color: var(--color-blue-300);
  }

  .slug-hint {
    font-size: var(--text-xs);
    color: var(--color-neutral-400);
    padding-left: 0.25rem;
    font-family: monospace;
  }

  .new-page-actions {
    display: flex;
    gap: 0.25rem;
  }

  .new-page-confirm,
  .new-page-cancel {
    flex: 1;
    padding: 0.2rem 0;
    font-size: var(--text-sm);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: background-color 120ms ease;
    border: 1px solid var(--color-neutral-300);
  }

  .new-page-confirm {
    background: var(--color-blue-600);
    color: var(--color-white);
    border-color: var(--color-blue-600);
  }

  .new-page-confirm:hover:not(:disabled) {
    background: var(--color-blue-700);
  }

  .new-page-confirm:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .new-page-cancel {
    background: var(--color-white);
    color: var(--color-neutral-600);
  }

  .new-page-cancel:hover {
    background: var(--color-neutral-100);
  }

  /* ── Footer ──────────────────────────────────────── */

  .sidebar-footer {
    margin-top: auto;
    padding-top: 1rem;
    padding-bottom: 0.5rem;
    text-align: center;
    color: var(--color-neutral-500);
    font-size: var(--text-xs);
    user-select: none;
  }
</style>

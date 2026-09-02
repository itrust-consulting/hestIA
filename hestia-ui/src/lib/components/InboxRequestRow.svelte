<script lang="ts">
  import type { Snippet } from 'svelte';

  type TypeVariant = 'join' | 'share' | 'outgoing' | 'system';

  type Props = {
    /** Short label shown in the type badge, e.g. "Join Request", "Sharing Request". */
    requestType: string;
    /** Controls the badge's color so request types stay visually distinct at a glance. */
    typeVariant?: TypeVariant;
    /** Who filed the request. */
    issuer: string;
    /** Epoch ms the request was filed. */
    date: number;
    /** Optional free-text message attached to the request. */
    message?: string | null;
    /** Row actions (e.g. accept/reject buttons) -- omit for a read-only row. */
    actions?: Snippet;
  };

  const { requestType, typeVariant = 'system', issuer, date, message, actions }: Props = $props();

  const formatDateTime = (ts: number) =>
    ts
      ? new Date(ts).toLocaleString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : '—';
</script>

<div class="request-row">
  <div class="request-row-body">
    <div class="request-row-top">
      <span
        class="request-type-badge"
        class:type-join={typeVariant === 'join'}
        class:type-share={typeVariant === 'share'}
        class:type-outgoing={typeVariant === 'outgoing'}
        class:type-system={typeVariant === 'system'}
      >
        {requestType}
      </span>
      <span class="request-issuer">{issuer}</span>
    </div>
    <div class="request-meta">
      <span class="request-date">{formatDateTime(date)}</span>
      {#if message}
        <span class="request-message">“{message}”</span>
      {/if}
    </div>
  </div>

  {#if actions}
    <div class="request-row-actions">
      {@render actions()}
    </div>
  {/if}
</div>

<style>
  .request-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.6rem 0.85rem;
    border-radius: var(--radius-lg);
    background: var(--color-neutral-50);
    border: 1px solid var(--color-neutral-200);
  }

  .request-row-body {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
  }

  .request-row-top {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .request-type-badge {
    display: inline-block;
    flex-shrink: 0;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    background: var(--color-neutral-100);
    color: var(--color-neutral-600);
  }
  .request-type-badge.type-join {
    background: var(--color-blue-50, #eff6ff);
    color: var(--color-blue-700, #1d4ed8);
  }
  .request-type-badge.type-share {
    background: var(--color-purple-100, #ede9fe);
    color: var(--color-purple-700, #6d28d9);
  }
  .request-type-badge.type-outgoing {
    background: var(--color-orange-100, #ffedd5);
    color: var(--color-orange-700, #c2410c);
  }
  .request-type-badge.type-system {
    background: var(--color-neutral-100);
    color: var(--color-neutral-600);
  }

  .request-issuer {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-neutral-800);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .request-meta {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    font-size: var(--text-xs);
    color: var(--color-neutral-500);
    min-width: 0;
  }

  .request-date {
    flex-shrink: 0;
  }

  .request-message {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-style: italic;
  }

  .request-row-actions {
    display: flex;
    gap: 0.4rem;
    flex-shrink: 0;
  }
</style>

<script lang="ts">
  import type { Citation } from '$lib/types';
  import { renderChatContent } from '$lib/render/renderChatContent';

  export let citations: Citation[] = [];
  export let onClose: () => void = () => {};

  const PREVIEW_LEN = 100;
  let expanded: Record<number, boolean> = {};
</script>

<aside class="citations-sidebar">
  <div class="sidebar-header">
    <h3>Sources</h3>
    <button class="close-btn" on:click={onClose} aria-label="Close sources">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" class="w-4 h-4">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </button>
  </div>

  <div class="sidebar-body">
    {#each citations as c, i}
      {@const preview = c.excerpt.slice(0, PREVIEW_LEN)}
      {@const truncated = c.excerpt.length > PREVIEW_LEN}
      <div class="citation-card">
        <div class="citation-source">{c.source}</div>
        {#if c.subject}<div class="citation-subject">{c.subject}</div>{/if}
        {#if c.path}<div class="citation-path">{c.path}</div>{/if}
        <div class="citation-excerpt">
          {@html renderChatContent(expanded[i] ? c.excerpt : preview)}{#if truncated && !expanded[i]}…{/if}
        </div>
        {#if truncated}
          <button class="show-more" on:click={() => (expanded[i] = !expanded[i])}>
            {expanded[i] ? 'show less' : 'show more'}
          </button>
        {/if}
      </div>
    {/each}
  </div>
</aside>

<style>
  .citations-sidebar {
    width: 22rem;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    border-left: 1px solid var(--color-neutral-200);
    background: var(--color-white);
    overflow: hidden;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--color-neutral-200);
    flex-shrink: 0;
  }

  .sidebar-header h3 {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-neutral-800);
  }

  .close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem;
    border-radius: var(--radius-md);
    background: none;
    border: none;
    color: var(--color-neutral-400);
    cursor: pointer;
    transition: background 0.1s, color 0.1s;
  }

  .close-btn:hover {
    background: var(--color-neutral-100);
    color: var(--color-neutral-800);
  }

  .sidebar-body {
    flex: 1 1 auto;
    overflow-y: auto;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .citation-card {
    padding: 0.75rem 1rem;
    border-radius: var(--radius-xl);
    border: 1px solid var(--color-neutral-200);
    background: var(--color-white);
    box-shadow: 0 12px 24px color-mix(in oklab, black 18%, transparent);
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .citation-source {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-blue-600);
    word-break: break-word;
  }

  .citation-subject {
    font-size: var(--text-xs);
    color: var(--color-neutral-600);
    word-break: break-word;
  }

  .citation-path {
    font-size: 0.65rem;
    color: var(--color-neutral-400);
    font-family: monospace;
    word-break: break-all;
    margin-bottom: 0.2rem;
  }

  .citation-excerpt {
    font-size: var(--text-sm);
    color: var(--color-neutral-700);
    line-height: 1.55;
    word-break: break-word;
  }

  .citation-excerpt :global(p) { margin: 0 0 0.4em; }
  .citation-excerpt :global(p:last-child) { margin-bottom: 0; }
  .citation-excerpt :global(ul), .citation-excerpt :global(ol) { margin: 0 0 0.4em 1.2em; padding: 0; }
  .citation-excerpt :global(li) { margin-bottom: 0.15em; }
  .citation-excerpt :global(code) { background: var(--color-neutral-100); border-radius: var(--radius-md); padding: 0.1em 0.3em; font-size: 0.9em; }
  .citation-excerpt :global(pre) { background: var(--color-neutral-50); border: 1px solid var(--color-neutral-200); border-radius: var(--radius-md); padding: 0.5rem; overflow-x: auto; }
  .citation-excerpt :global(strong) { color: var(--color-neutral-900); }
  .citation-excerpt :global(a) { color: var(--color-blue-600); }

  .show-more {
    background: none;
    border: none;
    padding: 0;
    color: var(--color-blue-600);
    font-size: var(--text-xs);
    cursor: pointer;
    text-decoration: underline;
    align-self: flex-start;
  }

  .show-more:hover {
    color: var(--color-blue-700);
  }
</style>

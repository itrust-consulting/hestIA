<script lang="ts">
  import type { Citation } from '$lib/types';
  import { renderChatContent } from '$lib/render/renderChatContent';
  import { tooltip } from '$lib/actions/tooltip';

  export let citations: Citation[];
  export let x: number;
  export let y: number;
  export let maxHeight: number;

  const PREVIEW_LEN = 100;

  let page = 0;
  let expanded = false;

  // Reset on new citation set
  $: if (citations?.length) { page = 0; expanded = false; }

  $: current = citations[page];
  $: total = citations.length;
  $: preview = current ? current.excerpt.slice(0, PREVIEW_LEN) : '';
  $: truncated = current ? current.excerpt.length > PREVIEW_LEN : false;
</script>

<div
  class="cite-popover"
  style="left:{x}px; top:{y}px; max-height:{maxHeight}px"
  role="tooltip"
>
  {#if total > 1}
    <div class="popover-nav">
      <button
        class="nav-btn"
        on:click={() => { page = Math.max(0, page - 1); expanded = false; }}
        disabled={page === 0}
        aria-label="Previous source"
        use:tooltip={"Previous source"}
      >‹</button>
      <span class="page-indicator">{page + 1} / {total}</span>
      <button
        class="nav-btn"
        on:click={() => { page = Math.min(total - 1, page + 1); expanded = false; }}
        disabled={page === total - 1}
        aria-label="Next source"
        use:tooltip={"Next source"}
      >›</button>
    </div>
  {/if}

  {#if current}
    <div class="popover-source">{current.source}</div>
    {#if current.subject}<div class="popover-subject">{current.subject}</div>{/if}
    {#if current.path}<div class="popover-path">{current.path}</div>{/if}
    <div class="popover-excerpt">
      {@html renderChatContent(expanded ? current.excerpt : preview)}{#if truncated && !expanded}…{/if}
    </div>
    {#if truncated}
      <button class="show-more" on:click={() => (expanded = !expanded)}>
        {expanded ? 'show less' : 'show more'}
      </button>
    {/if}
  {/if}
</div>

<style>
  .cite-popover {
    position: fixed;
    z-index: 2100;
    transform: translate(-50%, 8px);
    background: var(--color-white);
    color: var(--color-neutral-800);
    border: 1px solid var(--color-neutral-200);
    border-radius: var(--radius-xl);
    padding: 0.75rem 1rem;
    max-width: 22rem;
    min-width: 14rem;
    overflow-y: auto;
    box-shadow: 0 12px 24px color-mix(in oklab, black 18%, transparent);
    pointer-events: auto;
    font-size: var(--text-sm);
  }

  .popover-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--color-neutral-200);
  }

  .nav-btn {
    background: none;
    border: none;
    color: var(--color-neutral-400);
    cursor: pointer;
    font-size: 1.1rem;
    line-height: 1;
    padding: 0 0.3rem;
    border-radius: var(--radius-md);
    transition: background 0.1s, color 0.1s;
  }

  .nav-btn:not(:disabled):hover {
    color: var(--color-neutral-800);
    background: var(--color-neutral-100);
  }

  .nav-btn:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .page-indicator {
    font-size: var(--text-xs);
    color: var(--color-neutral-400);
    letter-spacing: 0.05em;
  }

  .popover-source {
    font-weight: 600;
    color: var(--color-blue-600);
    word-break: break-word;
    margin-bottom: 0.15rem;
  }

  .popover-subject {
    color: var(--color-neutral-600);
    font-size: var(--text-xs);
    word-break: break-word;
    margin-bottom: 0.1rem;
  }

  .popover-path {
    color: var(--color-neutral-400);
    font-size: 0.65rem;
    font-family: monospace;
    word-break: break-all;
    margin-bottom: 0.35rem;
  }

  .popover-excerpt {
    margin: 0 0 0.35rem;
    color: var(--color-neutral-700);
    line-height: 1.55;
    word-break: break-word;
  }

  .popover-excerpt :global(p) { margin: 0 0 0.4em; }
  .popover-excerpt :global(p:last-child) { margin-bottom: 0; }
  .popover-excerpt :global(ul), .popover-excerpt :global(ol) { margin: 0 0 0.4em 1.2em; padding: 0; }
  .popover-excerpt :global(li) { margin-bottom: 0.15em; }
  .popover-excerpt :global(code) { background: var(--color-neutral-100); border-radius: var(--radius-md); padding: 0.1em 0.3em; font-size: 0.9em; }
  .popover-excerpt :global(pre) { background: var(--color-neutral-50); border: 1px solid var(--color-neutral-200); border-radius: var(--radius-md); padding: 0.5rem; overflow-x: auto; }
  .popover-excerpt :global(strong) { color: var(--color-neutral-900); }
  .popover-excerpt :global(a) { color: var(--color-blue-600); }

  .show-more {
    background: none;
    border: none;
    padding: 0;
    color: var(--color-blue-600);
    font-size: var(--text-xs);
    cursor: pointer;
    text-decoration: underline;
  }

  .show-more:hover {
    color: var(--color-blue-700);
  }
</style>

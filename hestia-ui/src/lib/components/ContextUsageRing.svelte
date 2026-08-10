<script lang="ts">
  import { contextBudget, compacting, compactNow, announceCompaction } from '$lib/stores/contextBudget';
  import { activeConversationId } from '$lib/stores/conversations';
  import { addToast } from '$lib/stores/toast';
  import { tooltip } from '$lib/actions/tooltip';

  const RADIUS = 9;
  const CIRC = 2 * Math.PI * RADIUS;

  $: ratio = $contextBudget ? Math.min(1, $contextBudget.usedTokens / $contextBudget.maxTokens) : 0;
  // a fully-filled ring (ratio 1) is rotationally symmetric, so rotating it
  // while compacting produces no visible motion -- show a partial spinner
  // arc instead, which is visible at any fill level.
  $: dashArray = $compacting ? `${CIRC * 0.25} ${CIRC * 0.75}` : `${CIRC}`;
  $: dashOffset = $compacting ? 0 : CIRC * (1 - ratio);
  $: tooltipHtml = $compacting
    ? `<div class="ctx-tip"><div class="ctx-tip-label">Compacting…</div></div>`
    : $contextBudget
      ? `<div class="ctx-tip">
           <div class="ctx-tip-pct level-${level}">${Math.round(ratio * 100)}%</div>
           <div class="ctx-tip-label">of context window used</div>
           <div class="ctx-tip-action">Click to compact</div>
         </div>`
      : '';
  $: level = ratio < 0.6 ? 'low' : ratio < 0.85 ? 'mid' : 'high';

  async function onClick() {
    const cid = $activeConversationId;
    if (!cid || $compacting) return;
    const before = $contextBudget?.usedTokens ?? null;
    const status = await compactNow(cid);
    if (status === 'not_needed') {
      addToast('Already within budget — nothing to compact.', 'info');
    } else if (status === 'compacted') {
      const after = $contextBudget?.usedTokens ?? null;
      const freed = before != null && after != null ? before - after : null;
      announceCompaction(freed);
    }
  }
</script>

{#if $contextBudget}
  <button
    type="button"
    class="context-ring level-{level}"
    class:spinning={$compacting}
    on:click={onClick}
    disabled={$compacting}
    aria-label={$compacting ? 'Compacting conversation context…' : 'Context usage — click to compact now'}
    use:tooltip={tooltipHtml}
  >
    <svg viewBox="0 0 24 24" width="22" height="22">
      <circle class="track" cx="12" cy="12" r={RADIUS} />
      <circle
        class="fill"
        cx="12" cy="12" r={RADIUS}
        stroke-dasharray={dashArray}
        stroke-dashoffset={dashOffset}
        transform="rotate(-90 12 12)"
      />
    </svg>
  </button>
{/if}

<style>
  /* Normal flex child of .action-row now, alongside attach/send -- no longer
     absolutely positioned on top of the textarea. */
  .context-ring {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 9999px;
    border: none;
    background: transparent;
    cursor: pointer;
    padding: 0;
    flex-shrink: 0;
    transition: background 120ms ease, transform 120ms ease;
  }
  .context-ring:hover:not(:disabled) { background: var(--color-neutral-100); transform: scale(1.1); }
  .context-ring:disabled { cursor: default; opacity: 0.7; }
  .track { fill: none; stroke: var(--color-neutral-200); stroke-width: 2.5; }
  .fill { fill: none; stroke-width: 2.5; stroke-linecap: round; transition: stroke-dashoffset 200ms ease; }
  .level-low .fill  { stroke: var(--color-blue-600); }
  .level-mid .fill  { stroke: var(--color-yellow-500); }
  .level-high .fill { stroke: var(--color-red-600); }
  .spinning svg { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>

<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import { renderChatContent } from '$lib/render/renderChatContent';

  type Props = {
    open: boolean;
    onClose: () => void;
    filename: string;
    markdown: string;
  };

  let { open, onClose, filename, markdown }: Props = $props();

  let previewRaw = $state(false);
</script>

<Modal title={filename} {open} {onClose} wide={true}>
  <div class="preview-header">
    <div class="preview-toggle">
      <button class="toggle-btn" class:active={!previewRaw} onclick={() => (previewRaw = false)}>Preview</button>
      <button class="toggle-btn" class:active={previewRaw}  onclick={() => (previewRaw = true)}>Raw</button>
    </div>
  </div>

  {#if previewRaw}
    <textarea class="preview-area raw-editor" value={markdown} readonly spellcheck={false}></textarea>
  {:else}
    <div class="preview-area prose max-w-none">
      {#if markdown}
        {@html renderChatContent(markdown)}
      {:else}
        <span class="preview-placeholder">No content available.</span>
      {/if}
    </div>
  {/if}
</Modal>

<style>
.preview-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.5rem;
}

.preview-toggle {
  display: flex;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.toggle-btn {
  padding: 0.2rem 0.65rem;
  font-size: var(--text-xs);
  font-weight: 500;
  background: var(--color-white);
  color: var(--color-neutral-600);
  border: none;
  cursor: pointer;
}

.toggle-btn + .toggle-btn { border-left: 1px solid var(--color-neutral-300); }
.toggle-btn.active { background: var(--color-blue-600); color: white; }
.toggle-btn:not(.active):hover { background: var(--color-neutral-100); }

.preview-area {
  min-height: 20vw;
  max-height: 55vh;
  overflow-y: auto;
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  background: var(--color-neutral-50);
  font-size: var(--text-sm);
  line-height: 1.7;
}

.raw-editor {
  width: 100%;
  resize: none;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--text-xs);
  line-height: 1.6;
  white-space: pre;
  overflow-wrap: normal;
  overflow-x: auto;
}

.preview-placeholder {
  color: var(--color-neutral-400);
  font-size: var(--text-sm);
}
</style>

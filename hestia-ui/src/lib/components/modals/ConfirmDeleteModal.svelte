<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import { addToast } from '$lib/stores/toast';
  import type { Snippet } from 'svelte';

  type Props = {
    open: boolean;
    title: string;
    onClose: () => void;
    onConfirm: () => Promise<void>;
    children?: Snippet;
    confirmLabel?: string;
    successMessage?: string;
  };

  const { open, title, onClose, onConfirm, children, confirmLabel = 'Delete', successMessage }: Props = $props();

  let deleting = $state(false);
  let error = $state<string | null>(null);

  async function handleConfirm() {
    deleting = true;
    error = null;
    try {
      await onConfirm();
      if (successMessage) addToast(successMessage, 'success');
      onClose();
    } catch (e: any) {
      error = e?.message ?? 'Operation failed.';
    } finally {
      deleting = false;
    }
  }

  function handleClose() {
    if (!deleting) onClose();
  }
</script>

<Modal {title} {open} onClose={handleClose}>
  {@render children?.()}
  {#if error}
    <div class="error-box">{error}</div>
  {/if}
  <svelte:fragment slot="footer">
    <button class="danger-btn" onclick={handleConfirm} disabled={deleting}>
      {deleting ? 'Deleting…' : confirmLabel}
    </button>
  </svelte:fragment>
</Modal>

<style>
.danger-btn {
  background: var(--color-red-600);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-weight: 600;
  border: none;
  font-size: var(--text-sm);
}
.danger-btn:hover:not(:disabled) { background: var(--color-red-700); }
.danger-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.error-box {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-lg);
  margin-top: 0.75rem;
  font-size: var(--text-sm);
}
</style>

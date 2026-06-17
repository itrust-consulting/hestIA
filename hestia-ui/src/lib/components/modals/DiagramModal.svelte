<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';

  type Props = {
    open: boolean;
    onClose: () => void;
    svgHtml: string;
  };

  let { open, onClose, svgHtml }: Props = $props();
</script>

<Modal title="Diagram" {open} {onClose} wide={true}>
  <div class="diagram-wrapper">
    {@html svgHtml}
  </div>
</Modal>

<style>
  .diagram-wrapper {
    width: 100%;
    padding: 0.5rem 0;
  }

  .diagram-wrapper :global(svg) {
    display: block;
    width: 100%;
    height: auto;
    cursor: default;
  }
</style>

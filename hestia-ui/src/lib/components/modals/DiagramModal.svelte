<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import DOMPurify from 'isomorphic-dompurify';

  type Props = {
    open: boolean;
    onClose: () => void;
    svgHtml: string;
  };

  let { open, onClose, svgHtml }: Props = $props();

  const safeSvgHtml = $derived(DOMPurify.sanitize(svgHtml, { USE_PROFILES: { svg: true, svgFilters: true } }));
</script>

<Modal title="Diagram" {open} {onClose} wide={true}>
  <div class="diagram-wrapper">
    {@html safeSvgHtml}
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

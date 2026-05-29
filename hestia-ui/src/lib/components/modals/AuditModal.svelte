<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import InfoIcon from '../icons/infoIcon.svelte';
  import { tooltip } from '$lib/actions/tooltip';

  export let open = false;
  export let onClose: () => void;
</script>

<Modal {open} {onClose}>
  <span slot="title" class="title-with-info">
    <strong>Audit Assistant</strong>
    <span class="info-icon" use:tooltip={"<strong>What is the Audit Assistant?</strong>"}><InfoIcon/></span>
  </span>
  <div>
    <p class="flex justify-center">Work in progress.</p>
  </div>
</Modal>
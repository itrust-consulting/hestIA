<script lang="ts">
  import Modal from '$lib/components/Modal.svelte';
  import InfoIcon from '../icons/infoIcon.svelte';

  export let open = false;
  export let onClose: () => void;
</script>

<Modal {open} {onClose}>
  <span slot="title" class="title-with-info">
    <strong>Asset Manager</strong>
    <span class="info-icon"><InfoIcon/>
        <div class="tooltip">
        <strong>What is the Asset Manager?</strong><br/>

        </div>
    </span>
  </span>
  <div>
    <p class="flex justify-center">Work in progress.</p>
  </div>
</Modal>
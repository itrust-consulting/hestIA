<script lang="ts">
    export let title: string = "";
    export let open: boolean = false;
    export let onClose: () => void;
</script>

{#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="modal-overlay" on:click={onClose}>
        <div class="modal-window" on:click|stopPropagation>
            <header class="modal-header">
            <h2 class="modal-title">
                <slot name="title">{title}</slot>
            </h2>
            <button class="modal-close" on:click={onClose}>×</button>
            </header>

            <div class="modal-body">
                <slot />
            </div>
            <footer class="modal-footer">
                <slot name="footer" />

                <button on:click={onClose} class="close-btn">
                    Close
                </button>
            </footer>

        </div>
    </div>
{/if}

<style>
    .modal-overlay {
        position: fixed;
        inset: 0;
        background: color-mix(in oklab, black 30%, transparent);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 500;
    }

    .modal-window {
        width: 500px;
        max-width: 90%;
        background: var(--color-white);
        border-radius: var(--radius-xl);
        padding: 1.25rem;
        box-shadow: 0 6px 24px color-mix(in oklab, black 25%, transparent);
        animation: fadeIn 150ms ease-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .modal-header h2 {
        margin: 0;
        font-size: var(--text-lg);
    }
    .modal-close {
        font-size: 1.5rem;
        background: transparent;
        border: none;
        cursor: pointer;
        line-height: 1;
    }

    .modal-body {
        padding-top: .5rem;
    }

    .modal-footer {
        margin-top: 1.25rem;
        display: flex;
        justify-content: flex-end;       
        gap: 0.5rem;                     /* Space between buttons */
    }

    .close-btn {
        padding: .5rem 1rem;
        border-radius: var(--radius-md);
        background: var(--color-white);
        color: var(--color-neutral-600);
        cursor: pointer;
        border: 1px solid var(--color-neutral-200);
    }

    .close-btn:hover {
        background: var(--color-neutral-200);
    }


</style>
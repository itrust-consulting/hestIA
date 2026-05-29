<script>
    import { page } from '$app/state';
</script>

<div class="error-container">
    <div class="error-card">
        <div class="error-line">
            <span class="status">{page.status}</span>
            <span class="divider">|</span>
            <span class="message">
                {#if page.status === 401}
                    You need to log in to access this page.
                {:else if page.status === 403}
                    You do not have permission to view this page.
                {:else}
                    {page.error?.message}
                {/if}
            </span>
        </div>

        {#if page.status === 401}
            <div class="action">
                <a href="/login">Go to login</a>
            </div>
        {/if}
    </div>
</div>

<style>
    .error-container {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--color-neutral-50, #f9fafb);
    }

    .error-card {
        max-width: 32rem;
        padding: 2rem 2.5rem;
        background: var(--color-neutral-50);
        border-radius: 0.5rem;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
    }

    /* Horizontal message line */
    .error-line {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        text-align: left;
    }

    /* Status code */
    .status {
        font-size: 2.75rem;
        font-weight: 300;
        color: var(--color-neutral-900, #111827);
        line-height: 1;
    }

    /* Vertical divider */
    .divider {
        font-size: 2.75rem;
        font-weight: 300;
        color: var(--color-neutral-300, #d1d5db);
        line-height: 1;
    }

    .message {
        font-size: 0.95rem;
        color: var(--color-neutral-600, #4b5563);
        line-height: 1.4;
        max-width: 22rem;
        transform: translateY(0.35em); /* optical alignment */
    }

</style>
<script lang="ts">
  import { env } from '$env/dynamic/public';

  const currentVersion = env.PUBLIC_APP_VERSION;

</script>

<aside class="sidebar">

  <!-- Navigation -->
  <div class="sidebar-list">
    <h2>Users & Authentication</h2>
    <div class="sidebar-item">
        User Management
    </div>
        <div class="sidebar-item">
        Role Management
    </div>
        <div class="sidebar-item">
        Password Management
    </div>
    <h2>Database Management</h2>
        <div class="sidebar-item">
            User Database
        </div>
        <div class="sidebar-item">
            Knowledge Base
        </div>
    <h2>LLM Settings</h2>        
        <div class="sidebar-item">
            Configuration
        </div>
        <div class="sidebar-item">
            Agent Settings
        </div>
    <h2>System</h2>
        <div class="sidebar-item">
            Settings
        </div>
  </div>

  <!-- Footer -->
  <div class="sidebar-footer">
    <span class="version">{currentVersion}</span>
  </div>

</aside>

<style>

    .sidebar {
        position: sticky;
        top: var(--header-height);
        height: calc(100vh - var(--header-height));
        width: 280px;         /* your expanded width */
        flex-shrink: 0;
        overflow-y: auto;
        border-right: 1px solid var(--color-neutral-200);
        background: var(--color-neutral-200);
        padding: 1rem;
        display: flex;
        flex-direction: column;
        transition: width 200ms ease, transform 200ms ease, opacity 150ms ease, padding 200ms ease;
    }

    .sidebar h2 {
        font-size: var(--text-md);
        font-weight: 600;
        padding-bottom: .25rem;;
        border-bottom: 1px solid var(--color-neutral-400);
    }
    
    .sidebar-toggle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: var(--radius-lg);
        color: var(--color-neutral-700);
        border: none;
        cursor: pointer;
        transition: background-color 150ms ease;
    }
    .sidebar-toggle:hover {
        transform: scale(1.4);
    }

    .sidebar-closed {
        width: 56px;                 
        padding: 0.75rem;            
        transform: translateX(0);    
        opacity: 1;                 
        /* IMPORTANT: allow clicks so the toggle works */
        pointer-events: auto;
    }

    .sidebar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .sidebar-list {
        display: flex;
        flex-direction: column;
        gap: .5rem;
    }

    .sidebar-item {
        display: flex;
        align-items: center;
        gap: .75rem;
        line-height: 1.5rem;
        height: 1.75rem;
        padding: .75rem;
        border-radius: var(--radius-md);
        transition: background-color 120ms ease, color 120ms ease;
        cursor: pointer;
    }

    .sidebar-item:hover {
        border-radius: var(--radius-md);
        background: var(--color-white);
    }


    /* left accent bar */
    .sidebar-item.active::before {
        content: "";
        position: absolute;
        left: 0.25rem;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 70%;
        border-radius: 999px;
    }

    .sidebar-footer {
        margin-top: auto;                 
        padding-top: 1rem;
        padding-bottom: .5rem;
        text-align: center;
        color: var(--color-neutral-500);
        font-size: var(--text-xs);
        user-select: none;
    }
</style>
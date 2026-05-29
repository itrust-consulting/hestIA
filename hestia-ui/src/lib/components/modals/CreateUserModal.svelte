<script lang="ts">
    import { onMount } from "svelte";

    import Modal from '$lib/components/Modal.svelte';
    import { api } from '$lib/api/client';
    import { addToast } from '$lib/stores/toast';
    /** Props passed from parent */
    const { open, onClose, onSuccess, isAdmin } = $props();

    type Organization = {
    id: number;
    name: string;
    abbreviation: string;
    };

    type Role = {
    id: number;
    name: string;
    };

    let newUsername = $state("");
    let newEmail = $state("");
    let newFirstName = $state("");
    let newLastName = $state("");
    let assignRole = $state("");
    let assignOrganization = $state("");
    let defaultPassword = $state("");
    let expiresAt = $state<number | null>(null);

    let creatingOrg = $state(false);
    let newOrgName = $state("");
    let newOrgAbbreviation = $state("");

    let organizations: Organization[] = $state([]);
    let roles: Role[] = $state([]);

    async function loadRoles() {
        const res = await api.get('/api/admin/roles');
        if (!res.ok) return;
        roles = await res.json();
    }

    async function loadOrganizations() {
        try {
        const res = await fetch('/api/admin/organizations');
        if (!res.ok) return;
        const data = await res.json();
        organizations = data.organizations ?? [];
        } catch { /* leave empty — tenant field still editable */ }
    }

    onMount(loadRoles);
    onMount(loadOrganizations);

    function handleOrganizationChange(value: string) {
    if (value === "__new__") {
        creatingOrg = true;
        assignOrganization = "";
    } else {
        creatingOrg = false;
        assignOrganization = value;
    }
    }

    async function saveNewOrganization() {
        if (!newOrgName || !newOrgAbbreviation) return;

        try {
            const res = await api.post('/api/admin/organizations', {
                name: newOrgName,
                abbreviation: newOrgAbbreviation
            });

            if (!res.ok) {
                const msg = await res.text();
                throw new Error(msg || 'Failed to create organization');
            }

            const createdOrg: Organization = await res.json();

            organizations = [...organizations, createdOrg];

            assignOrganization = String(createdOrg.id);


            creatingOrg = false;
            newOrgName = "";
            newOrgAbbreviation = "";
        } catch (e: any) {
            addToast(e?.message ?? 'Failed to create organization.', 'error');
        }
    }

    // UI state
    let submitting = $state(false);

    async function createUser() {
        if (!assignRole) {
            addToast('Role is required.', 'error');
            return;
        }
        submitting = true;

        try {
            const res = await api.post('/api/admin/users', {
                username: newUsername,
                email: newEmail,
                first_name: newFirstName,
                last_name: newLastName,
                roles: [assignRole],
                organization: assignOrganization || null,
                password: defaultPassword,
                expires_at: expiresAt ? new Date(expiresAt).getTime() : null,
            });

            if (!res.ok) {
                const msg = await res.text();
                throw new Error(msg || 'Failed to create user');
            }

            addToast('User created successfully.', 'success');
            onSuccess?.();
            onClose();
        } catch {
            addToast('Could not create user.', 'error');
        } finally {
            submitting = false;
        }
    }

    function generatePassword(length = 16) {
        const charset =
            "ABCDEFGHJKLMNPQRSTUVWXYZ" + // no I / O
            "abcdefghijkmnopqrstuvwxyz" + // no l
            "23456789" +                  // no 0 / 1
            "!@#$%^&*";

        const values = new Uint32Array(length);
        crypto.getRandomValues(values);

        let password = "";
        for (let i = 0; i < length; i++) {
            password += charset[values[i] % charset.length];
        }

        defaultPassword = password;
    }

</script>

<Modal {open} {onClose}>
    <span slot="title">
        <strong>Create User</strong>
    </span>
    <div class="user-card">
        <div class="form-grid">
            <label>
                <span>Username<span class="required">*</span></span>
                <input class="input" type="text" bind:value={newUsername} />
            </label>

            <label>
                <span>Email<span class="required">*</span></span>
                <input class="input" type="email" bind:value={newEmail} />
            </label>

            <label>
                <span>First Name<span class="required">*</span></span>
                <input class="input" type="text" bind:value={newFirstName} />
            </label>

            <label>
                <span>Last Name<span class="required">*</span></span>
                <input class="input" type="text" bind:value={newLastName} />
            </label>

            <label>
                <span>Role<span class="required">*</span></span>
                <select class="input" bind:value={assignRole}>
                    <option value="" disabled selected hidden>Select role</option>
                        {#each roles as role}
                            <option value={role.id}>
                                {role.name}
                            </option>
                        {/each}
                </select>
            </label>

            <label>
                <span>Organization<span class="optional">(optional)</span></span>
                    <select
                        class="input"
                        bind:value={assignOrganization}
                        onchange={(e) =>
                            handleOrganizationChange(
                                (e.currentTarget as HTMLSelectElement).value
                            )
                        }
                    >
                        <option value="" disabled selected hidden>Select organization</option>

                        {#each organizations as org}
                            <option value={org.name}>
                                {org.name} ({org.abbreviation})
                            </option>
                        {/each}

                        <option value="__new__">✚ Add organization</option>
                    </select>
            </label>

            {#if creatingOrg}
            <div class="new-org-card">
                <label>
                <span>Organization Name</span>
                <input
                    type="text"
                    class="input"
                    bind:value={newOrgName}
                />
                </label>

                <label>
                <span>Abbreviation</span>
                <input
                    type="text"
                    class="input"
                    maxlength="8"
                    bind:value={newOrgAbbreviation}
                />
                </label>

                <button
                class="secondary-btn"
                onclick={saveNewOrganization}
                disabled={!newOrgName || !newOrgAbbreviation}
                >
                Add Organization
                </button>
            </div>
            {/if}

            <label class="full-width">
                <span>Default Password<span class="required">*</span></span>

                <div class="password-field">
                    <input
                        class="input"
                        type="password"
                        bind:value={defaultPassword}
                        placeholder="Enter or generate a password"
                    />

                    <button
                        type="button"
                        class="secondary-btn"
                        onclick={() => generatePassword()}
                        title="Generate random password"
                    >
                        Generate
                    </button>
                </div>
            </label>


            <label class="full-width">
                <span>Expiration Date<span class="optional">(optional)</span></span>
                    <input
                    class="input"
                    type="date"
                    onchange={(e) => {
                        const input = e.currentTarget as HTMLInputElement;
                        expiresAt = input.value
                        ? new Date(input.value).getTime()
                        : null;
                    }}
                    />
            </label>
        </div>
    </div>

    <span slot="footer" class="modal-footer">
        <button
            class="primary-btn"
            disabled={submitting || !newUsername || !newEmail || !defaultPassword || !assignRole}
            onclick={createUser}
        >
            {submitting ? 'Creating…' : 'Create User'}
        </button>
    </span>
</Modal>

<style>

.user-card {
    max-height: 70vh;
    display: flex;
    flex-direction: column;
}

.form-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem 1.5rem;
}

.new-org-card {
    grid-column: span 2;

    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem 1.5rem;

    padding: 0.85rem 1rem;
    margin-top: 0.25rem;

    background: linear-gradient(
        180deg,
        var(--color-neutral-50),
        var(--color-neutral-100)
    );

    border-radius: var(--radius-md);

    box-shadow:
        inset 0 0 0 1px var(--color-neutral-200),
        0 1px 2px rgba(0, 0, 0, 0.04);
}

.new-org-card button {
    grid-column: span 2;
    justify-self: flex-start;
}

.password-field {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.password-field .input {
    flex: 1;
}

label {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.875rem;
    color: var(--color-neutral-700);
}

label span {
    font-weight: 500;
}

.full-width {
    grid-column: span 2;
}

.input {
    padding: 0.45rem 0.6rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-neutral-300);
    background: var(--color-white);
    font: inherit;
}

.input:focus {
    outline: none;
    border-color: var(--color-blue-500);
    box-shadow: 0 0 0 1px var(--color-blue-200);
}

.required {
    color: var(--color-red-600);
    margin-left: 0.15rem;
}

.optional {
    font-weight: normal;
    font-size: 0.75rem;
    color: var(--color-neutral-500);
    margin-left: 0.25rem;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.75rem;
}

.primary-btn {
    background: var(--color-blue-600);
    color: white;
    border: none;
    padding: 0.5rem 1.2rem;
    border-radius: var(--radius-md);
    cursor: pointer;
}

.primary-btn:disabled {
    background: var(--color-blue-300);
    cursor: not-allowed;
}

.secondary-btn {
    background: var(--color-neutral-100);
    color: var(--color-neutral-800);
    border: 1px solid var(--color-neutral-300);
    padding: 0.5rem 1.2rem;
    border-radius: var(--radius-md);
    cursor: pointer;
}
</style>

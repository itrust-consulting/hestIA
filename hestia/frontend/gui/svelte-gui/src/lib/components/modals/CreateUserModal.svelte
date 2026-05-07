<script lang="ts">
    import { onMount } from "svelte";

    import Modal from '$lib/components/Modal.svelte';
    import ArrowLeftIcon from "../icons/arrowLeftIcon.svelte";
    /** Props passed from parent */
    const { open, onClose, isAdmin } = $props();
    
    type Organization = {
    id: number;
    name: string;
    abbreviation: string;
    };

    type Role = {
    id: number;
    name: string;
    };

    type Permission = {
    id: number;
    name: string;
    description: string;
    value_type: "boolean" | "list" | "map";
    options: Record<string, any>;
    };

    type RolePermission = {
    name: string;
    value: any;
    };

    type RolePermissionValue = any;

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
    let permissions: Permission[] = $state([]);
    let rolePermissions = $state<Record<string, RolePermissionValue>>({});
    let collections = $state<{ id: string; name: string }[]>([]);

    async function loadRoles() {
        const res = await fetch('/api/admin/roles');
        if (!res.ok) return;

        roles = await res.json();
    }
    
    async function loadOrganizations() {
        const res = await fetch('/api/admin/organizations');
        if (!res.ok) return;

        organizations = await res.json();
    }

    function parsePermissionValue(value: string) { 
        const v = value.trim();

        if (v === "true") return true;
        if (v === "false") return false;

        // JSON object / array
        if (
            (v.startsWith("{") && v.endsWith("}")) ||
            (v.startsWith("[") && v.endsWith("]"))
        ) {
            try {
                return JSON.parse(v);
            } catch {
                return value;
            }
        }

        // number
        const n = Number(v);
        if (!isNaN(n)) return n;

        return value;
    }

    
    async function loadPermissions() {
        const res = await fetch('/api/admin/permissions');
        if (!res.ok) return;

        permissions = await res.json();
    }

    async function loadRolePermissions(roleId: string) {
        const res = await fetch(`/api/admin/roles/${roleId}/permissions`);
        if (!res.ok) return;

        const list: RolePermission[] = await res.json();
        rolePermissions = Object.fromEntries(
            list.map(rp => [rp.name, parsePermissionValue(rp.value)])
        );
    }

    function getEffectivePermissionValue(permName: string, perm: Permission) {

        if (permName in rolePermissions) {
            return rolePermissions[permName];
        }

        // fallback to schema default
        if (perm.value_type === "boolean") return perm.options.default;
        if (perm.value_type === "list") return null;
        if (perm.value_type === "map") return {};

        return null;
    }

    async function loadCollections() {
        const res = await fetch('/api/collections');
        if (!res.ok) return;

        const data = await res.json();
        collections = data.collections;
    }

    type CollectionPermissionValue = {
        access: boolean;
        max_classification: number | null;
    };
    
    let userCollectionOverrides = $state<
        Record<string, CollectionPermissionValue>
    >({});
    let userBooleanPermissions = $state<Record<string, boolean>>({});

    function resolveCollectionPermission(
        collectionName: string
        ): CollectionPermissionValue {
        // 1. User override
        if (collectionName in userCollectionOverrides) {
            return userCollectionOverrides[collectionName];
        }

        const acl = rolePermissions["allowed_collections"] ?? {};

        // 2. Explicit role rule
        if (collectionName in acl) {
            return {
            access: Boolean(acl[collectionName].access),
            max_classification:
                acl[collectionName].max_classification === null
                ? null
                : Number(acl[collectionName].max_classification)
            };
        }

        // 3. Wildcard role rule
        if ("*" in acl) {
            return {
            access: Boolean(acl["*"].access),
            max_classification:
                acl["*"].max_classification === null
                ? null
                : Number(acl["*"].max_classification)
            };
        }

        // 4. Default deny
        return {
            access: false,
            max_classification: null
        };
        }

    onMount(loadRoles);
    onMount(loadOrganizations);
    onMount(loadPermissions);

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
            const res = await fetch('/api/admin/organizations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: newOrgName,
                abbreviation: newOrgAbbreviation,
            })
            });

            if (!res.ok) {
                const msg = await res.text();
            throw new Error(msg || 'Failed to create user');
            }

            const createdOrg: Organization = await res.json();

            organizations = [...organizations, createdOrg];

            assignOrganization = String(createdOrg.id);


            creatingOrg = false;
            newOrgName = "";
            newOrgAbbreviation = "";
        } catch (e) {
            console.error("Failed to create organization", e);
        }
    }

    // UI state
    let step = $state<1 | 2>(1);
    let submitting = $state(false);
    let error = $state("");

    async function continueToPermissions() {
        if (!assignRole) {
            error = "Role is required";
            return;
        }

        error = "";
        await loadRolePermissions(assignRole);
        await loadCollections();
        step = 2;
    }

    function backToUserInfo() {
        step = 1;
        rolePermissions = {};
    }

    async function resetPermssisions() {
        userCollectionOverrides = {};
    }

    function buildAllowedCollectionsPayload() {
        const result: Record<string, CollectionPermissionValue> = {};

        for (const collection of collections) {
            const val = resolveCollectionPermission(collection.name);
            result[collection.name] = {
                access: val.access,
                max_classification: val.max_classification
            };
        }

        return result;
    }
    
    function buildPermissionsPayload() {
        const payload: Record<string, any> = {};

        // Boolean permissions
        for (const perm of permissions) {
            if (perm.value_type === "boolean") {
                payload[perm.name] =
                    perm.name in userBooleanPermissions
                        ? userBooleanPermissions[perm.name]
                        : getEffectivePermissionValue(perm.name, perm);
            }
        }

        // Collection permissions
        payload["allowed_collections"] = buildAllowedCollectionsPayload();

        return payload;
    }

    // submit form
    async function createUser() {
        submitting = true;
        error = "";

        try {
            const permissionsPayload = buildPermissionsPayload();

            const res = await fetch('/api/admin/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: newUsername,
                    email: newEmail,
                    first_name: newFirstName,
                    last_name: newLastName,
                    role: assignRole,
                    organization: assignOrganization || null,
                    password: defaultPassword,
                    expires_at: expiresAt ? new Date(expiresAt).getTime() : null,

                    permissions: permissionsPayload
                })
            });

            if (!res.ok) {
                const msg = await res.text();
                throw new Error(msg || 'Failed to create user');
            }

            onClose();
        } catch (e) {
            error = 'Could not create user.';
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
        {#if step === 1}
            <strong>User information</strong>
        {/if}
        {#if step === 2}
            <strong>User permissions</strong>
        {/if}
    </span>
    {#if step === 1}
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
    {/if}
    {#if step === 2}
        <div class="permission-card">
            <div class="permission-toolbar">
                <button
                    class="back-button"
                    onclick={backToUserInfo}
                    aria-label="Back to user details"
                    title="Back"
                >
                    <ArrowLeftIcon />
                </button>

                <button
                    class="reset-button"
                    onclick={resetPermssisions}
                >
                    Reset
                </button>
            </div>
            <div class="permissions-panel full-width">
                {#each permissions as perm (perm.id)}
                    <div class="permission-row">
                        <span class="permission-description">
                            {perm.description}
                        </span>

                        <div class="permission-control">
                            {#if perm.value_type === "boolean"}
                                <select
                                    class="permission-select"
                                    value={getEffectivePermissionValue(perm.name, perm) ? "true" : "false"}
                                    onchange={(e) => {
                                        userBooleanPermissions = {
                                            ...userBooleanPermissions,
                                            [perm.name]: e.currentTarget.value === "true"
                                        };
                                    }}
                                >
                                    <option value="true">Enable</option>
                                    <option value="false">Disable</option>
                                </select>
                            {/if}
                        </div>
                    </div>

                    {#if perm.name === "allowed_collections"}
                        <div class="permission-group">

                            <!-- Header -->
                            <div class="permission-row header">
                                <span class="permission-header">Name</span>
                                <span class="permission-header">Access</span>
                                <span class="permission-header">Classification</span>
                            </div>

                            {#each collections as collection}
                                {@const val = resolveCollectionPermission(collection.name)}

                                <div class="permission-row nested">
                                    <!-- Collection name -->
                                    <span class="permission-description">
                                        {collection.name}
                                    </span>

                                    <!-- Access -->
                                    <select
                                        class="permission-select"
                                        value={val.access ? "true" : "false"}
                                        onchange={(e) => {
                                            const access = e.currentTarget.value === "true";

                                            userCollectionOverrides = {
                                                ...userCollectionOverrides,
                                                [collection.name]: {
                                                    access,
                                                    max_classification: access
                                                        ? val.max_classification
                                                        : null
                                                }
                                            };
                                        }}
                                    >
                                        <option value="true">Enable</option>
                                        <option value="false">Disable</option>
                                    </select>

                                    <!-- Max classification -->
                                    <select
                                        class="permission-select"
                                        disabled={!val.access}
                                        value={
                                            val.max_classification === null
                                                ? "null"
                                                : String(val.max_classification)
                                        }
                                        onchange={(e) => {
                                            const v = e.currentTarget.value;

                                            userCollectionOverrides = {
                                                ...userCollectionOverrides,
                                                [collection.name]: {
                                                    ...val,
                                                    max_classification:
                                                        v === "null" ? null : Number(v)
                                                }
                                            };
                                        }}
                                    >
                                        <option value="null">None</option>
                                        <option value="0">Public</option>
                                        <option value="1">Internal</option>
                                        <option value="2">Confidential</option>
                                        <option value="3">Restricted</option>
                                        <option value="4">Secret</option>
                                    </select>
                                </div>
                            {/each}
                        </div>
                    {/if}
                {/each}
            </div>
        </div>
    {/if}

    <span slot="footer" class="modal-footer">
        {#if step === 1}
            <button
                class="primary-btn"
                onclick={continueToPermissions}
            >
                Continue
            </button>
        {/if}
        {#if step === 2}
            <button
                class="primary-btn"
                onclick={createUser}
            >
                Create User
            </button>
        {/if}
    </span>
</Modal>

<style>

.user-card,
.permission-card {
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

.permission-card .permissions-panel {
    flex: 1;
    overflow-y: auto;

    padding-right: 0.5rem; /* avoids scrollbar overlap */
}


.permissions-panel {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

/* ============================
   Shared Grid Definition
   ============================ */

.permission-group {
    --perm-grid: 1fr 8rem 8rem;

    grid-column: span 2;
    margin-top: 0.75rem;
    padding-top: 0.25rem;

    border-top: 1px solid var(--color-neutral-200);
}

/* ============================
   Header Row
   ============================ */

.permission-row.header {
    display: grid;
    grid-template-columns: var(--perm-grid);
    align-items: center;
    gap: 0.5rem;

    padding: 0.15rem 0 0.4rem 0;
    margin-bottom: 0.35rem;

    border-bottom: 1px solid var(--color-neutral-200);
}

.permission-header {
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--color-neutral-500);

    text-transform: uppercase;
    letter-spacing: 0.04em;
    text-align: center;
}

.permission-row.header .permission-header:first-child {
    text-align: left;
}

/* ============================
   Default Permission Row
   ============================ */

.permission-row {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: 1rem;

    padding: 0.25rem 0;
}

.permission-description {
    font-size: 0.75rem;
    color: var(--color-neutral-700);
    line-height: 1.3;
}

.permission-control {
    display: flex;
    justify-content: flex-end;
}

/* ============================
   Collection Rows (Nested)
   ============================ */

.permission-row.nested {
    display: grid;
    grid-template-columns: var(--perm-grid);
    align-items: center;
    gap: 0.5rem;

    padding: 0.2rem 0;
}

.permission-row.nested .permission-description {
    padding-left: 0.5rem;
    font-size: 0.75rem;
    color: var(--color-neutral-700);
}

/* ============================
   Select Inputs
   ============================ */

.permission-select {
    min-width: 8rem;
    padding: 0.25rem 0.45rem;

    font-size: 0.75rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-neutral-300);
    background: var(--color-white);

    color: var(--color-neutral-800);
}

.permission-select:focus {
    outline: none;
    border-color: var(--color-blue-500);
}

/* Slightly more compact in nested rows */
.permission-row.nested .permission-select {
    min-width: 7.5rem;
}

/* Disabled state */
.permission-select:disabled {
    background: var(--color-neutral-100);
    color: var(--color-neutral-400);
    border-color: var(--color-neutral-200);
    cursor: not-allowed;
}

/* ============================
   Permission toolbar
   ============================ */

.permission-toolbar {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 0.5rem;

    margin-bottom: 0.5rem;
}

/* ============================
   Back button (icon only)
   ============================ */

.back-button {
    background: none;
    border: none;
    padding: 0.2rem;
    cursor: pointer;

    color: var(--color-neutral-700);
    display: flex;
    align-items: center;
    justify-content: center;
}

.back-button svg {
    width: 1.1rem;
    height: 1.1rem;
}

.back-button:hover {
    color: var(--color-neutral-900);
}

.back-button:focus {
    outline: none;
    box-shadow: 0 0 0 2px var(--color-blue-200);
    border-radius: 999px;
}

.reset-button {
    margin-left: auto;
    background: transparent;
    padding: 0.25rem 0.4rem;

    font-size: 0.75rem;
    color: var(--color-neutral-600);
    cursor: pointer;
}

.reset-button:hover {
    color: var(--color-neutral-900);
    text-decoration: underline;
}
</style>
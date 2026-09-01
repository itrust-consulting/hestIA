<script lang="ts">
  import { invalidateAll } from '$app/navigation';
  import Modal from '$lib/components/Modal.svelte';
  import ShowIcon from '$lib/components/icons/showIcon.svelte';
  import { addToast } from '$lib/stores/toast';
  import { parseJsonParam, parseParamValue } from '$lib/llmParamSchemas';

  const { data } = $props();

  type AuthMode = 'local' | 'ldap' | 'oidc';

  const s = data.authSettings;

  // ── Mode & password policy ──────────────────────────────────────────────
  let authMode = $state<AuthMode>(s.auth_mode);
  let passwordMinLength = $state(String(s.password_min_length));
  let maxFailedAttempts = $state(String(s.max_failed_attempts));
  let lockoutDurationMinutes = $state(String(s.lockout_duration_minutes));
  let tokenLifetimeMinutes = $state(String(s.token_lifetime_minutes));
  let auditLogs = $state<boolean>(s.audit_logs);

  let tokenSecretKey = $state('');
  let tokenSecretKeyVisible = $state(false);

  // ── OIDC ─────────────────────────────────────────────────────────────────
  let oidcProviderUrl = $state(s.oidc_provider_url);
  let oidcClientId = $state(s.oidc_client_id);
  let oidcClientSecret = $state('');
  let oidcClientSecretVisible = $state(false);
  let oidcScopes = $state((s.oidc_scopes ?? []).join(', '));
  let oidcRoleClaim = $state(s.oidc_role_claim);
  let oidcRoleMapping = $state(s.oidc_role_mapping ? JSON.stringify(s.oidc_role_mapping, null, 2) : '');
  let oidcOrgClaim = $state(s.oidc_org_claim);
  let oidcOrgMapping = $state(s.oidc_org_mapping ? JSON.stringify(s.oidc_org_mapping, null, 2) : '');

  // ── LDAP ─────────────────────────────────────────────────────────────────
  let ldapHost = $state(s.ldap_host);
  let ldapPort = $state(String(s.ldap_port));
  let ldapSearchBase = $state(s.ldap_search_base);
  let ldapUserAttribute = $state(s.ldap_user_attribute);
  let ldapMailAttribute = $state(s.ldap_mail_attribute);
  let ldapUseSsl = $state<boolean>(s.ldap_use_ssl);
  let ldapValidateCert = $state<boolean>(s.ldap_validate_cert);
  let ldapBindDn = $state(s.ldap_bind_dn ?? '');
  let ldapBindPassword = $state('');
  let ldapBindPasswordVisible = $state(false);
  let ldapUserDnTemplate = $state(s.ldap_user_dn_template ?? '');
  let ldapAllowedGroups = $state((s.ldap_allowed_groups ?? []).join(', '));
  let ldapGroupMapping = $state(s.ldap_group_mapping ? JSON.stringify(s.ldap_group_mapping, null, 2) : '');

  // ── Save flow ────────────────────────────────────────────────────────────
  let savePhase = $state<'testing' | 'saving' | null>(null);
  let saveError = $state<string | null>(null);
  let jsonErrors = $state<Record<string, string>>({});
  let confirmOpen = $state(false);

  const modeChanged = $derived(authMode !== s.auth_mode);
  const keyChanged = $derived(tokenSecretKey.trim() !== '');

  function buildTestPayload() {
    return {
      auth_mode: authMode,
      oidc_provider_url: oidcProviderUrl.trim(),
      oidc_client_id: oidcClientId.trim(),
      oidc_client_secret: oidcClientSecret.trim() || null,
      ldap_host: ldapHost.trim(),
      ldap_port: parseInt(ldapPort, 10) || 636,
      ldap_search_base: ldapSearchBase.trim(),
      ldap_user_attribute: ldapUserAttribute.trim(),
      ldap_mail_attribute: ldapMailAttribute.trim(),
      ldap_use_ssl: ldapUseSsl,
      ldap_validate_cert: ldapValidateCert,
      ldap_bind_dn: ldapBindDn.trim() || null,
      ldap_bind_password: ldapBindPassword.trim() || null,
    };
  }

  function buildSavePayload() {
    return {
      auth_mode: authMode,
      password_min_length: parseInt(passwordMinLength, 10),
      max_failed_attempts: parseInt(maxFailedAttempts, 10),
      lockout_duration_minutes: parseInt(lockoutDurationMinutes, 10),
      token_lifetime_minutes: parseInt(tokenLifetimeMinutes, 10),
      token_secret_key: tokenSecretKey.trim() || null,
      audit_logs: auditLogs,
      ldap_group_mapping: parseJsonParam(ldapGroupMapping).value ?? null,
      oidc_provider_url: oidcProviderUrl.trim(),
      oidc_client_id: oidcClientId.trim(),
      oidc_client_secret: oidcClientSecret.trim() || null,
      oidc_scopes: parseParamValue('string-list', oidcScopes),
      oidc_role_claim: oidcRoleClaim.trim(),
      oidc_role_mapping: parseJsonParam(oidcRoleMapping).value ?? null,
      oidc_org_claim: oidcOrgClaim.trim(),
      oidc_org_mapping: parseJsonParam(oidcOrgMapping).value ?? null,
      ldap_host: ldapHost.trim(),
      ldap_port: parseInt(ldapPort, 10),
      ldap_search_base: ldapSearchBase.trim(),
      ldap_user_attribute: ldapUserAttribute.trim(),
      ldap_mail_attribute: ldapMailAttribute.trim(),
      ldap_use_ssl: ldapUseSsl,
      ldap_validate_cert: ldapValidateCert,
      ldap_bind_dn: ldapBindDn.trim() || null,
      ldap_bind_password: ldapBindPassword.trim() || null,
      ldap_user_dn_template: ldapUserDnTemplate.trim() || null,
      ldap_allowed_groups: parseParamValue('string-list', ldapAllowedGroups),
    };
  }

  function validate(): boolean {
    const errs: Record<string, string> = {};
    const roleMapping = parseJsonParam(oidcRoleMapping);
    const orgMapping = parseJsonParam(oidcOrgMapping);
    const groupMapping = parseJsonParam(ldapGroupMapping);
    if (roleMapping.error) errs.oidcRoleMapping = roleMapping.error;
    if (orgMapping.error) errs.oidcOrgMapping = orgMapping.error;
    if (groupMapping.error) errs.ldapGroupMapping = groupMapping.error;
    jsonErrors = errs;
    if (Object.keys(errs).length > 0) {
      saveError = 'Fix invalid JSON in the highlighted field(s) before saving.';
      return false;
    }

    const numericFields: [string, string][] = [
      ['Min password length', passwordMinLength],
      ['Max failed attempts', maxFailedAttempts],
      ['Lockout duration', lockoutDurationMinutes],
      ['Token lifetime', tokenLifetimeMinutes],
    ];
    if (authMode === 'ldap') numericFields.push(['LDAP port', ldapPort]);
    for (const [label, raw] of numericFields) {
      if (raw.trim() === '' || Number.isNaN(parseInt(raw, 10))) {
        saveError = `${label} must be a whole number.`;
        return false;
      }
    }
    if (tokenSecretKey.trim() !== '' && tokenSecretKey.trim().length < 32) {
      saveError = 'Signing key must be at least 32 characters.';
      return false;
    }
    return true;
  }

  async function handleSave(skipConfirm = false) {
    saveError = null;
    if (!validate()) return;

    if ((modeChanged || keyChanged) && !skipConfirm) {
      confirmOpen = true;
      return;
    }

    savePhase = 'testing';
    try {
      if (authMode !== 'local') {
        const testRes = await fetch('/api/admin/auth-settings/test', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(buildTestPayload()),
        });
        const testData = await testRes.json().catch(() => ({}));
        if (!testRes.ok || testData.ok === false) {
          throw new Error(testData.error ?? testData.detail ?? 'Connection test failed.');
        }
      }

      savePhase = 'saving';
      const res = await fetch('/api/admin/auth-settings', {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(buildSavePayload()),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast(
        'Authentication settings updated.' + (modeChanged || keyChanged ? ' Active sessions (including yours) have been invalidated.' : ''),
        'success'
      );
      confirmOpen = false;
      tokenSecretKey = '';
      oidcClientSecret = '';
      ldapBindPassword = '';
      await invalidateAll();
    } catch (e: any) {
      saveError = e.message ?? 'Failed to save.';
    } finally {
      savePhase = null;
    }
  }
</script>

<div class="admin-content">
  <h1 class="title">Authentication</h1>

  <div class="section-header"><h3>Mode &amp; Password Policy</h3></div>
  <div class="panel">
    <div class="form-stack">
      <label class="field">
        <span>Authentication mode</span>
        <select bind:value={authMode}>
          <option value="local">Local</option>
          <option value="ldap">LDAP</option>
          <option value="oidc">OIDC</option>
        </select>
        {#if modeChanged}<span class="hint warning-hint">Changing this will invalidate all active sessions, including yours.</span>{/if}
      </label>

      <div class="field-row">
        <label class="field">
          <span>Min. password length</span>
          <input type="text" inputmode="numeric" bind:value={passwordMinLength} />
        </label>
        <label class="field">
          <span>Max failed attempts</span>
          <input type="text" inputmode="numeric" bind:value={maxFailedAttempts} />
        </label>
        <label class="field">
          <span>Lockout duration (minutes)</span>
          <input type="text" inputmode="numeric" bind:value={lockoutDurationMinutes} />
        </label>
        <label class="field">
          <span>Token lifetime (minutes)</span>
          <input type="text" inputmode="numeric" bind:value={tokenLifetimeMinutes} />
        </label>
      </div>

      <label class="checkbox-row">
        <input type="checkbox" bind:checked={auditLogs} />
        <span>Enable auth audit logging</span>
      </label>

      <label class="field">
        <span>Signing key <span class="hint">(leave blank to keep existing)</span></span>
        <div class="password-row">
          <input type={tokenSecretKeyVisible ? 'text' : 'password'} bind:value={tokenSecretKey} placeholder={s.has_token_secret_key ? '••••••••' : 'required, min. 32 characters'} />
          <button type="button" class="icon-btn" title={tokenSecretKeyVisible ? 'Hide' : 'Show'} onclick={() => (tokenSecretKeyVisible = !tokenSecretKeyVisible)}>
            <ShowIcon />
          </button>
        </div>
        {#if keyChanged}<span class="hint warning-hint">Changing this will invalidate all active sessions, including yours.</span>{/if}
      </label>
    </div>
  </div>

  <div class="section-header"><h3>OIDC Settings</h3></div>
  <div class="panel">
    <details class="parameter-settings" open={s.auth_mode === 'oidc'}>
      <summary>OIDC provider configuration</summary>
      <div class="form-stack">
        <label class="field">
          <span>Provider URL</span>
          <input type="text" bind:value={oidcProviderUrl} placeholder="https://keycloak.example.com/realms/myrealm" />
        </label>
        <label class="field">
          <span>Client ID</span>
          <input type="text" bind:value={oidcClientId} />
        </label>
        <label class="field">
          <span>Client secret <span class="hint">(leave blank to keep existing)</span></span>
          <div class="password-row">
            <input type={oidcClientSecretVisible ? 'text' : 'password'} bind:value={oidcClientSecret} placeholder={s.has_oidc_client_secret ? '••••••••' : 'optional'} />
            <button type="button" class="icon-btn" title={oidcClientSecretVisible ? 'Hide' : 'Show'} onclick={() => (oidcClientSecretVisible = !oidcClientSecretVisible)}>
              <ShowIcon />
            </button>
          </div>
        </label>
        <label class="field">
          <span>Scopes <span class="hint">(comma-separated)</span></span>
          <input type="text" bind:value={oidcScopes} placeholder="openid, profile, email" />
        </label>
        <label class="field">
          <span>Role claim</span>
          <input type="text" bind:value={oidcRoleClaim} />
        </label>
        <label class="field">
          <span>Role mapping <span class="hint">(JSON object: OIDC role → local roles)</span></span>
          <textarea
            class="param-json"
            rows="3"
            bind:value={oidcRoleMapping}
            onblur={() => { const { error } = parseJsonParam(oidcRoleMapping); jsonErrors = { ...jsonErrors, oidcRoleMapping: error ?? '' }; }}
            placeholder={'unset, e.g. {"keycloak-admin": ["admin"]}'}
          ></textarea>
          {#if jsonErrors.oidcRoleMapping}<div class="field-error">{jsonErrors.oidcRoleMapping}</div>{/if}
        </label>
        <label class="field">
          <span>Org claim</span>
          <input type="text" bind:value={oidcOrgClaim} />
        </label>
        <label class="field">
          <span>Org mapping <span class="hint">(JSON object: OIDC org → tenant name)</span></span>
          <textarea
            class="param-json"
            rows="3"
            bind:value={oidcOrgMapping}
            onblur={() => { const { error } = parseJsonParam(oidcOrgMapping); jsonErrors = { ...jsonErrors, oidcOrgMapping: error ?? '' }; }}
            placeholder={'unset, e.g. {"Acme Corp": "acme"}'}
          ></textarea>
          {#if jsonErrors.oidcOrgMapping}<div class="field-error">{jsonErrors.oidcOrgMapping}</div>{/if}
        </label>
      </div>
    </details>
  </div>

  <div class="section-header"><h3>LDAP Settings</h3></div>
  <div class="panel">
    <details class="parameter-settings" open={s.auth_mode === 'ldap'}>
      <summary>LDAP directory configuration</summary>
      <div class="form-stack">
        <div class="field-row">
          <label class="field">
            <span>Host</span>
            <input type="text" bind:value={ldapHost} />
          </label>
          <label class="field">
            <span>Port</span>
            <input type="text" inputmode="numeric" bind:value={ldapPort} />
          </label>
        </div>
        <label class="field">
          <span>Search base</span>
          <input type="text" bind:value={ldapSearchBase} />
        </label>
        <div class="field-row">
          <label class="field">
            <span>User attribute</span>
            <input type="text" bind:value={ldapUserAttribute} />
          </label>
          <label class="field">
            <span>Mail attribute</span>
            <input type="text" bind:value={ldapMailAttribute} />
          </label>
        </div>
        <label class="checkbox-row">
          <input type="checkbox" bind:checked={ldapUseSsl} />
          <span>Use SSL</span>
        </label>
        <label class="checkbox-row">
          <input type="checkbox" bind:checked={ldapValidateCert} />
          <span>Validate certificate</span>
        </label>
        <label class="field">
          <span>Bind DN</span>
          <input type="text" bind:value={ldapBindDn} />
        </label>
        <label class="field">
          <span>Bind password <span class="hint">(leave blank to keep existing)</span></span>
          <div class="password-row">
            <input type={ldapBindPasswordVisible ? 'text' : 'password'} bind:value={ldapBindPassword} placeholder={s.has_ldap_bind_password ? '••••••••' : 'optional'} />
            <button type="button" class="icon-btn" title={ldapBindPasswordVisible ? 'Hide' : 'Show'} onclick={() => (ldapBindPasswordVisible = !ldapBindPasswordVisible)}>
              <ShowIcon />
            </button>
          </div>
        </label>
        <label class="field">
          <span>User DN template</span>
          <input type="text" bind:value={ldapUserDnTemplate} />
        </label>
        <label class="field">
          <span>Allowed groups <span class="hint">(comma-separated)</span></span>
          <input type="text" bind:value={ldapAllowedGroups} />
        </label>
        <label class="field">
          <span>Group mapping <span class="hint">(JSON object: LDAP group → local roles)</span></span>
          <textarea
            class="param-json"
            rows="3"
            bind:value={ldapGroupMapping}
            onblur={() => { const { error } = parseJsonParam(ldapGroupMapping); jsonErrors = { ...jsonErrors, ldapGroupMapping: error ?? '' }; }}
            placeholder={'unset, e.g. {"admins": ["admin"]}'}
          ></textarea>
          {#if jsonErrors.ldapGroupMapping}<div class="field-error">{jsonErrors.ldapGroupMapping}</div>{/if}
        </label>
      </div>
    </details>
  </div>

  {#if saveError}<div class="field-error save-error">{saveError}</div>{/if}
  <div class="save-row">
    <button class="action-btn" onclick={() => handleSave()} disabled={savePhase !== null}>
      {savePhase === 'testing' ? 'Testing…' : savePhase === 'saving' ? 'Saving…' : 'Save'}
    </button>
  </div>
</div>

<Modal title="Confirm session invalidation" open={confirmOpen} onClose={() => (confirmOpen = false)}>
  <p>
    {#if modeChanged && keyChanged}
      Changing the authentication mode and signing key will invalidate all active sessions, including your own.
    {:else if modeChanged}
      Changing the authentication mode will invalidate all active sessions, including your own.
    {:else}
      Changing the signing key will invalidate all active sessions, including your own.
    {/if}
    You will need to log in again. Continue?
  </p>
  <svelte:fragment slot="footer">
    <button class="danger-btn" onclick={() => handleSave(true)} disabled={savePhase !== null}>
      {savePhase === 'testing' ? 'Testing…' : savePhase === 'saving' ? 'Saving…' : 'Continue'}
    </button>
  </svelte:fragment>
</Modal>

<style>
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-6xl);
  margin-inline: auto;
}

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 1rem;
}

.section-header { margin: 1.5rem 0 0.75rem; }
.section-header h3 {
  font-size: var(--text-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-neutral-600);
}

.panel {
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.form-stack { display: flex; flex-direction: column; gap: 0.875rem; }

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
}
.field input[type="text"],
.field input[type="password"],
.field select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
  font-family: inherit;
  width: 100%;
}
.field input:focus, .field select:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}

.field-row { display: flex; gap: 1rem; flex-wrap: wrap; }
.field-row .field { flex: 1; min-width: 10rem; }

.hint { font-weight: 400; color: var(--color-neutral-400); font-size: var(--text-xs); }
.warning-hint { color: var(--color-red-600); font-weight: 500; display: block; margin-top: 0.15rem; }

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-neutral-700);
}
.checkbox-row input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
}

.password-row { display: flex; gap: 0.5rem; align-items: stretch; }
.password-row input { flex: 1; min-width: 0; }

.icon-btn {
  background: transparent;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  cursor: pointer;
  padding: 0.4rem 0.6rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover { background: var(--color-neutral-100); }

.parameter-settings { display: flex; flex-direction: column; gap: 0.6rem; }
.parameter-settings summary {
  cursor: pointer; font-size: var(--text-sm); font-weight: 500;
  color: var(--color-neutral-500); user-select: none;
}
.parameter-settings summary:hover { color: var(--color-neutral-700); }
.parameter-settings .form-stack { margin-top: 0.6rem; }

.param-json {
  padding: 0.4rem 0.5rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--color-white);
  width: 100%;
  resize: vertical;
}

.field-error {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
}
.save-error { margin-top: 1rem; }

.save-row { margin-top: 1rem; }

.action-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

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
</style>

# Read-Only Demo Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add administrator and demo credentials so demo visitors can browse all existing content but cannot create, edit, upload, confirm, retry, or start any business operation.

**Architecture:** Next.js owns login and a signed HttpOnly role session, then forwards the authenticated role and an internal secret to FastAPI from server-side calls. FastAPI is the final authorization boundary: every business mutation requires an authenticated `admin` role, while read routes remain available to both roles. The UI keeps restricted features visible but marks them as locked and intercepts demo submissions with one consistent explanation.

**Tech Stack:** Next.js proxy and Route Handlers, Web Crypto HMAC sessions, Node.js scrypt password hashes, React context, FastAPI dependencies, Pydantic settings, Vitest, Pytest

**Spec:** `docs/superpowers/specs/2026-08-27-readonly-demo-and-mobile-layout-design.md`

## Global Constraints

- Roles are exactly `admin` and `demo`.
- Demo access is read-only across the whole application, not only on merchant endpoints.
- FastAPI must reject unauthorized writes even when the caller bypasses the visible UI.
- Production credentials, password hashes, session secrets, and internal API secrets never enter Git or browser bundles.
- Local development remains usable without credentials and defaults to `admin` only when `ACCESS_AUTH_REQUIRED=false`.
- No registration, password recovery, user-management UI, tenant isolation, quotas, or partner billing is added.
- Existing read routes and existing administrator workflows must remain compatible.

---

### Task 1: Define FastAPI access identities and the administrator dependency

**Files:**
- Create: `services/api/app/core/access.py`
- Modify: `services/api/app/core/config.py`
- Modify: `services/api/app/main.py`
- Create: `services/api/tests/test_access_control.py`

**Interfaces:**
- Produces: `AccessRole = Literal["admin", "demo"]`.
- Produces: `AccessIdentity(role: AccessRole)`.
- Produces: `get_access_identity(x_access_role, x_internal_auth, settings) -> AccessIdentity`.
- Produces: `require_admin(identity) -> AccessIdentity` and `AdminAccessDep`.
- Consumes: `Settings.internal_api_secret` and `Settings.access_auth_required`.

- [ ] **Step 1: Add failing unit tests for trusted and untrusted identities**

Create `services/api/tests/test_access_control.py` with direct dependency tests:

```python
import pytest
from fastapi import HTTPException

from app.core.access import AccessIdentity, get_access_identity, require_admin
from app.core.config import Settings


def settings(*, required: bool = True) -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        access_auth_required=required,
        internal_api_secret="server-secret",
    )


def test_valid_internal_admin_identity_is_accepted() -> None:
    identity = get_access_identity("admin", "server-secret", settings())
    assert identity == AccessIdentity(role="admin")
    assert require_admin(identity) == identity


def test_demo_identity_cannot_mutate() -> None:
    identity = get_access_identity("demo", "server-secret", settings())
    with pytest.raises(HTTPException) as error:
        require_admin(identity)
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    ("role", "secret"),
    [("admin", "wrong"), ("owner", "server-secret"), (None, None)],
)
def test_required_auth_rejects_untrusted_headers(role, secret) -> None:
    with pytest.raises(HTTPException) as error:
        get_access_identity(role, secret, settings())
    assert error.value.status_code == 401


def test_local_development_defaults_to_admin_when_auth_is_disabled() -> None:
    assert get_access_identity(None, None, settings(required=False)).role == "admin"
```

- [ ] **Step 2: Run the access tests and verify the missing-module failure**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_access_control.py -q
```

Expected: FAIL because `app.core.access` and the new settings do not exist.

- [ ] **Step 3: Add the access settings and dependency**

Add to `Settings` in `services/api/app/core/config.py`:

```python
access_auth_required: bool = False
internal_api_secret: SecretStr = SecretStr("")
```

Create `services/api/app/core/access.py`:

```python
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings

AccessRole = Literal["admin", "demo"]


class AccessIdentity(BaseModel):
    role: AccessRole


def get_access_identity(
    x_access_role: Annotated[str | None, Header()] = None,
    x_internal_auth: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> AccessIdentity:
    if not settings.access_auth_required:
        return AccessIdentity(role="admin")
    expected = settings.internal_api_secret.get_secret_value()
    if not expected or x_internal_auth != expected or x_access_role not in {"admin", "demo"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access identity")
    return AccessIdentity(role=x_access_role)


AccessIdentityDep = Annotated[AccessIdentity, Depends(get_access_identity)]


def require_admin(identity: AccessIdentityDep) -> AccessIdentity:
    if identity.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo access is read-only")
    return identity


AdminAccessDep = Annotated[AccessIdentity, Depends(require_admin)]
```

- [ ] **Step 4: Allow the trusted headers through local CORS**

Extend `allow_headers` in `services/api/app/main.py` to include `X-Access-Role` and `X-Internal-Auth`. Do not add wildcard origins.

- [ ] **Step 5: Run the focused tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_access_control.py tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the access identity boundary**

```powershell
git add services/api/app/core/access.py services/api/app/core/config.py services/api/app/main.py services/api/tests/test_access_control.py
git commit -m "feat: add trusted access roles"
```

---

### Task 2: Protect every existing FastAPI business mutation

**Files:**
- Modify: `services/api/app/merchants/router.py`
- Modify: `services/api/app/queries/router.py`
- Modify: `services/api/app/scans/router.py`
- Modify: `services/api/app/mobile_checks/router.py`
- Modify: `services/api/app/platform_audits/router.py`
- Modify: `services/api/app/reports/router.py`
- Modify: `services/api/tests/conftest.py`
- Create: `services/api/tests/test_demo_write_routes.py`

**Interfaces:**
- Consumes: `AdminAccessDep` from Task 1.
- Produces: a FastAPI route graph where every POST, PUT, PATCH, DELETE, upload, confirmation, cleanup, retry, refresh, and manual-result handler requires `AdminAccessDep`.

- [ ] **Step 1: Add an authenticated test client helper**

In `services/api/tests/conftest.py`, add:

```python
@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-Access-Role": "admin", "X-Internal-Auth": "test-internal-secret"}


@pytest.fixture
def demo_headers() -> dict[str, str]:
    return {"X-Access-Role": "demo", "X-Internal-Auth": "test-internal-secret"}
```

Do not enable required authentication globally for the existing suite. In `test_demo_write_routes.py`, override `get_settings` with `Settings(database_url="sqlite+pysqlite:///:memory:", access_auth_required=True, internal_api_secret="test-internal-secret")` and clear the override after that module's client fixture yields. Existing router suites continue using their current auth-disabled test default.

- [ ] **Step 2: Write route-level rejection tests before changing routers**

Create `services/api/tests/test_demo_write_routes.py`. Use the existing database override pattern and assert representative mutations are blocked before validation or service work:

```python
@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("post", "/merchants", {"name": "访客商家", "city": "杭州"}),
        ("patch", "/merchants/00000000-0000-0000-0000-000000000001", {"name": "改名"}),
        ("post", "/merchants/00000000-0000-0000-0000-000000000001/query-sets/generate", {}),
        ("post", "/scan-runs", {"merchant_id": "00000000-0000-0000-0000-000000000001", "query_set_id": "00000000-0000-0000-0000-000000000002", "adapter_name": "ark"}),
        ("post", "/merchants/00000000-0000-0000-0000-000000000001/platform-audits", {}),
        ("post", "/merchants/00000000-0000-0000-0000-000000000001/mobile-validation-sets", {}),
    ],
)
def test_demo_cannot_call_business_mutations(client, demo_headers, method, path, json) -> None:
    response = getattr(client, method)(path, json=json, headers=demo_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Demo access is read-only"
```

Add one read assertion such as `GET /merchants` returning `200` for `demo_headers`.

- [ ] **Step 3: Run the new tests and verify mutations are currently reachable**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_demo_write_routes.py -q
```

Expected: FAIL because current write routes do not require an administrator.

- [ ] **Step 4: Add `AdminAccessDep` to every write handler**

Import `AdminAccessDep` in each router and add an unused named parameter to every business mutation:

```python
def create_merchant(
    payload: MerchantCreate,
    session: SessionDep,
    _access: AdminAccessDep,
) -> MerchantRead:
```

Apply the same pattern to all currently discovered writes:

- merchant create/update, profile replace/parse, local-context refresh;
- query generation/cleanup/update;
- scan create/retry/manual results;
- platform audit create/adopt;
- mobile validation create/select, round create/confirm, source discovery, evidence upload;
- report manual check creation.

Do not add the dependency to GET handlers, `/health`, or `/system/status`.

- [ ] **Step 5: Add a route-inventory regression assertion**

In `services/api/tests/test_demo_write_routes.py`, inspect each FastAPI `APIRoute` whose methods intersect `{"POST", "PUT", "PATCH", "DELETE"}`. Walk its dependency tree and assert one dependency call is `require_admin`. This catches a newly added write route even when it has dynamic path parameters or a request body that would otherwise fail validation before a useful route test can be assembled. The initial exclusion set is empty.

- [ ] **Step 6: Run focused router suites once**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_access_control.py tests/test_demo_write_routes.py tests/merchants/test_router.py tests/queries/test_router.py tests/scans/test_router.py tests/mobile_checks/test_router.py tests/platform_audits/test_router.py tests/reports/test_router.py -q
```

Expected: PASS with existing administrator test flows updated to send `admin_headers` or use auth-disabled local defaults intentionally.

- [ ] **Step 7: Commit API write protection**

```powershell
git add services/api/app services/api/tests/conftest.py services/api/tests/test_demo_write_routes.py services/api/tests/*/test_router.py
git commit -m "feat: enforce demo read only access"
```

---

### Task 3: Add signed Next.js sessions and two-credential login

**Files:**
- Create: `apps/web/src/lib/access-role.ts`
- Create: `apps/web/src/lib/access-session.ts`
- Create: `apps/web/src/lib/access-password.ts`
- Create: `apps/web/src/app/login/page.tsx`
- Create: `apps/web/src/app/api/access/login/route.ts`
- Create: `apps/web/src/app/api/access/logout/route.ts`
- Create: `apps/web/scripts/hash-access-password.mjs`
- Modify: `apps/web/src/proxy.ts`
- Create: `apps/web/tests/access-session.test.ts`
- Create: `apps/web/tests/access-password.test.ts`
- Create: `apps/web/tests/proxy-access.test.ts`

**Interfaces:**
- Produces: `type AccessRole = "admin" | "demo"`.
- Produces: `createAccessSession(role, secret, now?) -> Promise<string>`.
- Produces: `verifyAccessSession(value, secret, now?) -> Promise<AccessRole | null>`.
- Produces: `verifyPassword(password, encodedHash) -> boolean` for `scrypt$<salt>$<hash>` values.
- Produces: the HttpOnly cookie `access_session` with a 12-hour lifetime.
- Produces: authenticated requests carrying the server-created `x-access-role` request header.

- [ ] **Step 1: Write failing pure-function tests for sessions and passwords**

Test all of the following:

- an `admin` session verifies as `admin`;
- a `demo` session verifies as `demo`;
- a changed payload or signature verifies as `null`;
- an expired session verifies as `null`;
- the checked-in test hash accepts `演示密码-123` and rejects a different password;
- timing-safe comparison is used for equal-length password hashes.

Use a fixed session secret and fixed timestamp in tests so signatures are deterministic.

- [ ] **Step 2: Run the tests and verify the modules are missing**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/access-session.test.ts tests/access-password.test.ts
```

Expected: FAIL because the access modules do not exist.

- [ ] **Step 3: Implement role and signed-session primitives**

In `access-role.ts`, export the role type, `ACCESS_SESSION_COOKIE`, and `isAccessRole(value)`.

In `access-session.ts`, encode a JSON payload shaped as:

```ts
type AccessSessionPayload = {
  role: AccessRole;
  expiresAt: number;
};
```

Sign the base64url payload with Web Crypto `HMAC` + `SHA-256`. Verify the signature before parsing the role and expiry. Never put a password or password hash in the cookie.

- [ ] **Step 4: Implement scrypt hash verification and the local hash generator**

`access-password.ts` must parse `scrypt$<hex salt>$<hex hash>`, derive with Node `scryptSync`, and compare using `timingSafeEqual`.

`scripts/hash-access-password.mjs` must read the password interactively from stdin without echoing it, generate a random 16-byte salt, derive 64 bytes with scrypt, and print only the encoded hash. It must not accept the password as a command-line argument because shell history is persistent.

- [ ] **Step 5: Build the login page and access Route Handlers**

The login page contains username and password fields, posts to `/api/access/login`, shows a neutral error state, and explains that visitors should use the credentials provided by the project owner.

The POST handler at `/api/access/login` compares the submitted username against:

- `ACCESS_ADMIN_USERNAME` + `ACCESS_ADMIN_PASSWORD_HASH`;
- `ACCESS_DEMO_USERNAME` + `ACCESS_DEMO_PASSWORD_HASH`.

On success, sign the matching role with `ACCESS_SESSION_SECRET`, set `access_session` as `HttpOnly`, `SameSite=Lax`, `Secure` in production, `Path=/`, and redirect to `/`. On failure, redirect to `/login?error=invalid` without revealing which field was wrong.

The POST handler at `/api/access/logout` deletes only `access_session` and redirects to `/login`. It performs no other cookie or browser-state cleanup.

- [ ] **Step 6: Extend the existing proxy without losing merchant restoration**

Make `proxy` asynchronous. Preserve `merchantContextRedirect`, but authenticate first:

1. Allow `/login`, `/api/access/login`, Next static assets, image assets, and favicon without a session. Allow `/api/access/logout` only after the current session verifies.
2. When `ACCESS_AUTH_REQUIRED` is not `true`, attach `x-access-role: admin` and continue.
3. When required, verify `access_session`; redirect invalid sessions to `/login`.
4. Delete any incoming `x-access-role`, set the verified role on cloned request headers, and call `NextResponse.next({ request: { headers } })`.
5. Apply the existing merchant-context redirect only after authentication.

Replace the current route-list matcher with `matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"]` so authentication covers every application page and Server Action request, not only merchant-scoped routes. Extract the pure path decision into a testable helper and cover public paths, required login, admin, demo, matching of ordinary pages and Server Actions, and preservation of merchant query parameters in `proxy-access.test.ts`.

- [ ] **Step 7: Run focused web tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/access-session.test.ts tests/access-password.test.ts tests/proxy-access.test.ts tests/merchant-context.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit the login and session layer**

```powershell
git add apps/web/src/lib/access-role.ts apps/web/src/lib/access-session.ts apps/web/src/lib/access-password.ts apps/web/src/app/login apps/web/src/app/api/access apps/web/src/proxy.ts apps/web/scripts/hash-access-password.mjs apps/web/tests
git commit -m "feat: add admin and demo login sessions"
```

---

### Task 4: Propagate the role through Next.js server calls and block bypasses

**Files:**
- Create: `apps/web/src/lib/server-access.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/queries/actions.ts`
- Modify: `apps/web/src/app/scans/actions.ts`
- Modify: `apps/web/src/app/merchants/[id]/actions.ts`
- Modify: `apps/web/src/app/mobile-checks/actions.ts`
- Modify: `apps/web/src/app/platform-audits/actions.ts`
- Create: `apps/web/tests/server-access.test.ts`
- Modify: `apps/web/tests/query-actions.test.ts`
- Modify: `apps/web/tests/profile-actions.test.ts`

**Interfaces:**
- Consumes: `x-access-role` set by Task 3 and `INTERNAL_API_SECRET` from server environment.
- Produces: `getServerAccessRole() -> Promise<AccessRole>`.
- Produces: `requireServerAdmin() -> Promise<void>` throwing `DemoReadOnlyError` for `demo`.
- Produces: `trustedApiHeaders(init?) -> Promise<Headers>` containing `X-Access-Role` and `X-Internal-Auth`.

- [ ] **Step 1: Write failing tests for server role propagation**

Mock `next/headers` and verify:

- admin calls receive both trusted headers;
- demo read calls receive role `demo`;
- demo mutation guards throw `DemoReadOnlyError` before `fetch` runs;
- the internal secret never appears in a client component or `NEXT_PUBLIC_*` variable.

- [ ] **Step 2: Implement `server-access.ts`**

Use `headers()` to read the proxy-created role. When auth is disabled, default to `admin`; when auth is required and the role is missing, throw an authentication error. Read `INTERNAL_API_SECRET` only in this server-only module.

- [ ] **Step 3: Add the guard to every Server Action**

The first executable line of every business mutation action is:

```ts
await requireServerAdmin();
```

This must precede parsing uploads, calling `fetch`, revalidation, or redirection. Convert API calls in actions to use `trustedApiHeaders`, merging `content-type` and `x-filename` without replacing the trusted headers.

- [ ] **Step 4: Add trusted headers to mutation helpers in `api.ts`**

All POST, PUT and PATCH helpers use `trustedApiHeaders`. GET helpers may include the role for consistent API audit context but must not expose the internal secret to browser-side code.

- [ ] **Step 5: Run focused action tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/server-access.test.ts tests/query-actions.test.ts tests/profile-actions.test.ts tests/mobile-checks.test.ts tests/platform-audits.test.tsx
```

Expected: PASS and demo tests prove `fetch` was not called.

- [ ] **Step 6: Commit role propagation and action guards**

```powershell
git add apps/web/src/lib/server-access.ts apps/web/src/lib/api.ts apps/web/src/app apps/web/tests
git commit -m "feat: guard server mutations by role"
```

---

### Task 5: Add the visible demo mode and locked action feedback

**Files:**
- Create: `apps/web/src/components/access-role-provider.tsx`
- Create: `apps/web/src/components/demo-mutation-guard.tsx`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/components/app-shell.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Modify: write-capable pages and components under `apps/web/src/app` and `apps/web/src/components`
- Create: `apps/web/tests/demo-mode.test.tsx`
- Modify: `apps/web/tests/layout.test.tsx`

**Interfaces:**
- Produces: `AccessRoleProvider({ role, children })` and `useAccessRole()`.
- Produces: `DemoMutationGuard` that intercepts marked actions in demo mode.
- Consumes: `data-requires-admin="true"` on every write form or write button.

- [ ] **Step 1: Write failing UI tests**

Verify that:

- `admin` renders without an演示模式 badge;
- `demo` renders the badge;
- clicking or submitting an element marked `data-requires-admin="true"` in demo mode prevents the action;
- the message `当前为演示权限，实际操作请联系管理员。` is announced with `role="status"`;
- read-only navigation is not intercepted.

- [ ] **Step 2: Read the role in the root layout**

In the server `RootLayout`, read `x-access-role` from `headers()`, set `data-access-role` on `<body>`, and wrap children in `AccessRoleProvider`. Preserve `suppressHydrationWarning`.

- [ ] **Step 3: Implement one delegated mutation guard**

`DemoMutationGuard` listens for click and submit events inside the application shell. In demo mode it blocks the nearest element carrying `data-requires-admin="true"`, keeps focus on the locked control, and exposes one dismissible status message. It does not intercept links, filters, merchant switching, disclosures, evidence viewing, or report navigation unless they are explicitly marked.

- [ ] **Step 4: Mark all existing write controls**

Add `data-requires-admin="true"` to every UI entry that creates, saves, parses, generates, starts, retries, confirms, adopts, uploads, or cleans up data. Add a visible lock label using text such as `演示模式不可操作`; do not rely on color alone and do not remove the feature name.

- [ ] **Step 5: Add the global demo badge and styles**

Show `演示模式` in the desktop navigation rail and mobile header. Style locked controls with reduced emphasis while retaining WCAG-readable text. Add `aria-disabled="true"` in demo mode but do not use the native `disabled` attribute when the control must still provide the explanatory message.

- [ ] **Step 6: Run focused component tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/demo-mode.test.tsx tests/layout.test.tsx tests/navigation.test.tsx tests/home.test.tsx tests/query-table.test.tsx tests/mobile-check-workspace.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit the visible demo experience**

```powershell
git add apps/web/src/app apps/web/src/components apps/web/src/styles/globals.css apps/web/tests
git commit -m "feat: show locked demo mode controls"
```

---

### Task 6: Document secure configuration and verify the permission boundary

**Files:**
- Modify: `README.md`
- Modify: `docs/operator-guide.md`
- Create or modify: `services/api/.env.example`
- Create or modify: `apps/web/.env.example`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: the environment names introduced in Tasks 1–4.
- Produces: copy-safe setup instructions that never contain actual credentials.

- [ ] **Step 1: Add non-secret environment templates**

Document these exact variables without real values:

```dotenv
ACCESS_AUTH_REQUIRED=true
ACCESS_ADMIN_USERNAME=
ACCESS_ADMIN_PASSWORD_HASH=
ACCESS_DEMO_USERNAME=
ACCESS_DEMO_PASSWORD_HASH=
ACCESS_SESSION_SECRET=
INTERNAL_API_SECRET=
```

API receives `ACCESS_AUTH_REQUIRED` and `INTERNAL_API_SECRET`; Web receives all seven. The production values for `ACCESS_SESSION_SECRET` and `INTERNAL_API_SECRET` must be independently generated high-entropy secrets.

- [ ] **Step 2: Document password-hash generation and role behavior**

Add the interactive command:

```powershell
cd apps/web
node scripts/hash-access-password.mjs
```

Explain that admin credentials permit writes, demo credentials are read-only, and rotating `ACCESS_SESSION_SECRET` signs everyone out.

- [ ] **Step 3: Run the single relevant verification set**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_access_control.py tests/test_demo_write_routes.py -q
cd ../../apps/web
npm.cmd test -- --run tests/access-session.test.ts tests/access-password.test.ts tests/proxy-access.test.ts tests/server-access.test.ts tests/demo-mode.test.tsx
npm.cmd run build
```

Expected: all tests PASS and the production web build succeeds.

- [ ] **Step 4: Manually verify both roles locally**

Start with auth required, sign in once as `demo`, and verify existing pages load while create, save, upload, generate, start and retry operations show the demo explanation and create no records. Sign out by clearing only the application session through the provided logout action, sign in as `admin`, and verify one reversible test mutation succeeds.

- [ ] **Step 5: Commit configuration documentation**

```powershell
git add README.md docs/operator-guide.md services/api/.env.example apps/web/.env.example .gitignore
git commit -m "docs: configure admin and demo access"
```

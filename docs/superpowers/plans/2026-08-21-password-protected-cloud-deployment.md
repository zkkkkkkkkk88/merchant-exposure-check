# Password-Protected Cloud Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production Docker deployment that keeps application services private, exposes the project through a password-protected Cloudflare Quick Tunnel, and persists PostgreSQL data on the Tencent Cloud Ubuntu server.

**Architecture:** Caddy is the only application gateway and applies one shared Basic Auth credential to both pages and `/api`. It routes pages to a standalone Next.js container and strips `/api` before routing API calls to FastAPI; a Cloudflare Quick Tunnel makes only Caddy reachable over a random HTTPS URL. FastAPI, the scan worker, PostgreSQL, and Next.js communicate only on the Compose network.

**Tech Stack:** Docker Compose, Caddy 2, Cloudflare `cloudflared`, Next.js standalone output, FastAPI/Uvicorn, PostgreSQL 17, Vitest, Pytest

**Spec:** `docs/superpowers/specs/2026-08-21-password-protected-cloud-deployment-design.md`

**Execution amendment (approved 2026-08-21):** The local Windows machine does not have Docker and the user chose not to install Docker Desktop. Source-text-only Docker/Caddy tests are omitted; real image builds, Compose resolution, authentication, routing, and persistence checks run on the Tencent Cloud server before completion.

## Global Constraints

- Target host is Ubuntu 24.04, 2 CPU, 2 GB RAM, 40 GB SSD, with approximately 2 GB Swap already enabled.
- The initial public entry point is a random `https://*.trycloudflare.com` Quick Tunnel URL; no domain or fixed URL is required.
- Every page and API request is protected by one shared Basic Auth credential.
- PostgreSQL, FastAPI, worker, and Next.js publish no host ports; ports `3000`, `8000`, and `5432` remain private.
- Real passwords, private keys, and API keys never enter Git, image layers, browser bundles, screenshots, or deployment documentation.
- Existing Windows development scripts and the current development Compose workflow must continue to work.
- Quick Tunnel is explicitly a testing-only service; the documentation must explain that its URL can change when the tunnel process is recreated.

---

### Task 1: Separate server-internal and browser API addresses

**Files:**
- Create: `apps/web/src/lib/api-base.ts`
- Create: `apps/web/src/lib/server-api-base.ts`
- Create: `apps/web/tests/api-base.test.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/mobile-checks/actions.ts`
- Modify: `apps/web/src/app/platform-audits/actions.ts`
- Modify: `apps/web/src/components/service-status.tsx`

**Interfaces:**
- Produces: `resolveServerApiBaseUrl(env?: ApiEnvironment): string`, returning `API_BASE_URL`, then legacy `NEXT_PUBLIC_API_BASE_URL`, then `http://127.0.0.1:8000`.
- Produces: `resolvePublicApiBaseUrl(value?: string): string`, returning an explicit public value or the same-origin `/api` path.
- Produces: `SERVER_API_BASE_URL: string` from `apps/web/src/lib/server-api-base.ts`, keeping server environment access out of the browser module.
- Consumers: all Next.js server-side API calls use `SERVER_API_BASE_URL`; the client-only service status calls `resolvePublicApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL)` so Next.js can inline the public value safely.

- [ ] **Step 1: Write the failing resolver tests**

Create `apps/web/tests/api-base.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { resolvePublicApiBaseUrl, resolveServerApiBaseUrl } from "@/lib/api-base";

describe("API base URL selection", () => {
  it("prefers the private server API address", () => {
    expect(resolveServerApiBaseUrl({
      API_BASE_URL: "http://api:8000",
      NEXT_PUBLIC_API_BASE_URL: "https://public.invalid/api",
    })).toBe("http://api:8000");
  });

  it("preserves the existing local development fallback", () => {
    expect(resolveServerApiBaseUrl({})).toBe("http://127.0.0.1:8000");
  });

  it("uses the same-origin API route in the browser by default", () => {
    expect(resolvePublicApiBaseUrl()).toBe("/api");
    expect(resolvePublicApiBaseUrl("http://127.0.0.1:8000")).toBe(
      "http://127.0.0.1:8000",
    );
  });
});
```

- [ ] **Step 2: Run the resolver test and verify the missing module failure**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/api-base.test.ts
```

Expected: FAIL because `@/lib/api-base` does not exist.

- [ ] **Step 3: Implement the URL resolvers**

Create `apps/web/src/lib/api-base.ts`:

```ts
type ApiEnvironment = {
  API_BASE_URL?: string;
  NEXT_PUBLIC_API_BASE_URL?: string;
};

export function resolveServerApiBaseUrl(
  env: ApiEnvironment = {},
): string {
  return env.API_BASE_URL
    ?? env.NEXT_PUBLIC_API_BASE_URL
    ?? "http://127.0.0.1:8000";
}

export function resolvePublicApiBaseUrl(
  value?: string,
): string {
  return value ?? "/api";
}
```

Create `apps/web/src/lib/server-api-base.ts`:

```ts
import { resolveServerApiBaseUrl } from "@/lib/api-base";

export const SERVER_API_BASE_URL = resolveServerApiBaseUrl(process.env);
```

- [ ] **Step 4: Route server and client consumers through the correct resolver**

In `apps/web/src/lib/api.ts`, `apps/web/src/app/mobile-checks/actions.ts`, and `apps/web/src/app/platform-audits/actions.ts`, import and use:

```ts
import { SERVER_API_BASE_URL } from "@/lib/server-api-base";

const API_BASE_URL = SERVER_API_BASE_URL;
```

In `apps/web/src/components/service-status.tsx`, import and use:

```ts
import { resolvePublicApiBaseUrl } from "@/lib/api-base";

const API_BASE_URL = resolvePublicApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL,
);
```

Remove the duplicated `process.env.NEXT_PUBLIC_API_BASE_URL` expressions from those four files.

- [ ] **Step 5: Run the focused web tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/api-base.test.ts tests/query-actions.test.ts tests/profile-actions.test.ts
```

Expected: all selected tests PASS and existing server-action calls still default to `http://127.0.0.1:8000`.

- [ ] **Step 6: Commit the API address split**

```powershell
git add apps/web/src/lib/api-base.ts apps/web/src/lib/server-api-base.ts apps/web/src/lib/api.ts apps/web/src/app/mobile-checks/actions.ts apps/web/src/app/platform-audits/actions.ts apps/web/src/components/service-status.tsx apps/web/tests/api-base.test.ts
git commit -m "feat: separate internal and public api routes"
```

---

### Task 2: Build production-ready application images

**Files:**
- Modify: `apps/web/next.config.ts`
- Modify: `apps/web/tests/next-config.test.ts`
- Modify: `apps/web/Dockerfile`
- Create: `apps/web/tests/dockerfile.test.ts`
- Modify: `services/api/Dockerfile`
- Create: `services/api/tests/test_production_dockerfile.py`

**Interfaces:**
- Produces: a web image whose runtime command is `node server.js` on `0.0.0.0:3000`.
- Produces: an API image containing the application plus `alembic.ini` and the `migrations/` tree.
- Consumers: `docker-compose.prod.yml` in Task 3 builds these images from `apps/web` and `services/api`.

- [ ] **Step 1: Add failing Next.js production configuration assertions**

Extend `apps/web/tests/next-config.test.ts`:

```ts
it("emits a standalone production server for the runtime image", () => {
  expect(nextConfig.output).toBe("standalone");
});
```

Create `apps/web/tests/dockerfile.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const dockerfile = readFileSync(
  fileURLToPath(new URL("../Dockerfile", import.meta.url)),
  "utf8",
);

describe("production web image", () => {
  it("builds standalone output and starts the minimal server", () => {
    expect(dockerfile).toContain("RUN npm run build");
    expect(dockerfile).toContain('CMD ["node", "server.js"]');
    expect(dockerfile).not.toContain('CMD ["npm", "run", "dev"');
  });

  it("runs the final image as a non-root user", () => {
    expect(dockerfile).toContain("USER nextjs");
  });
});
```

- [ ] **Step 2: Add the failing API image assertions**

Create `services/api/tests/test_production_dockerfile.py`:

```python
from pathlib import Path


def test_api_image_contains_database_migrations() -> None:
    dockerfile = Path(__file__).parents[1] / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")

    assert "COPY alembic.ini ./" in content
    assert "COPY migrations ./migrations" in content
    assert 'CMD ["uvicorn", "app.main:app"' in content
    assert "--reload" not in content
```

- [ ] **Step 3: Run the image tests and verify they fail**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/next-config.test.ts tests/dockerfile.test.ts
cd ../../services/api
.\.venv\Scripts\python.exe -m pytest tests/test_production_dockerfile.py -q
```

Expected: FAIL because standalone output, the production web stages, and migration copies are absent.

- [ ] **Step 4: Enable standalone Next.js output**

Add this property to `nextConfig` in `apps/web/next.config.ts` while preserving the existing upload and origin settings:

```ts
output: "standalone",
```

- [ ] **Step 5: Replace the web Dockerfile with a multi-stage production build**

Replace `apps/web/Dockerfile` with:

```dockerfile
FROM node:24-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS builder
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 6: Make the API image migration-capable**

Replace `services/api/Dockerfile` with:

```dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN python -m pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 7: Run focused tests and build both images**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/next-config.test.ts tests/dockerfile.test.ts
docker build -t merchant-exposure-web:test .
cd ../../services/api
.\.venv\Scripts\python.exe -m pytest tests/test_production_dockerfile.py -q
docker build -t merchant-exposure-api:test .
```

Expected: tests PASS and both Docker builds finish successfully.

- [ ] **Step 8: Commit the production images**

```powershell
git add apps/web/next.config.ts apps/web/tests/next-config.test.ts apps/web/Dockerfile apps/web/tests/dockerfile.test.ts services/api/Dockerfile services/api/tests/test_production_dockerfile.py
git commit -m "build: add production application images"
```

---

### Task 3: Add the private production stack and authenticated gateway

**Files:**
- Create: `docker-compose.prod.yml`
- Create: `deploy/Caddyfile`
- Create: `deploy/.env.production.example`
- Modify: `.gitignore`
- Create: `services/api/tests/test_production_stack.py`

**Interfaces:**
- Consumes: `web` image accepting `API_BASE_URL=http://api:8000`; API image accepting existing service environment variables.
- Produces: Compose services `db`, `migrate`, `api`, `worker`, `web`, `gateway`, and `tunnel`.
- Produces: Caddy route `/api/*` to `api:8000` with prefix stripping; all other paths route to `web:3000`.
- Produces: deployment secret file path `deploy/.env.production`, excluded from Git.

- [ ] **Step 1: Write failing production-stack contract tests**

Create `services/api/tests/test_production_stack.py`:

```python
from pathlib import Path


ROOT = Path(__file__).parents[3]


def test_production_stack_keeps_internal_ports_private() -> None:
    compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    for service in ("db:", "migrate:", "api:", "worker:", "web:", "gateway:", "tunnel:"):
        assert service in compose
    for published_port in ('"3000:3000"', '"8000:8000"', '"5432:5432"'):
        assert published_port not in compose
    assert "service_completed_successfully" in compose
    assert "cloudflare/cloudflared" in compose
    assert "http://gateway:80" in compose


def test_gateway_authenticates_pages_and_api() -> None:
    caddyfile = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")

    assert "basic_auth" in caddyfile
    assert "{$AUTH_USERNAME}" in caddyfile
    assert "{$AUTH_PASSWORD_HASH}" in caddyfile
    assert "handle_path /api/*" in caddyfile
    assert "reverse_proxy api:8000" in caddyfile
    assert "reverse_proxy web:3000" in caddyfile


def test_production_secrets_are_ignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "deploy/.env.production" in gitignore
```

- [ ] **Step 2: Run the stack contract tests and verify they fail**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_production_stack.py -q
```

Expected: FAIL because the production Compose file, gateway configuration, and secret ignore rule do not exist.

- [ ] **Step 3: Add the authenticated Caddy routing configuration**

Create `deploy/Caddyfile`:

```caddyfile
:80 {
    basic_auth {
        {$AUTH_USERNAME} {$AUTH_PASSWORD_HASH}
    }

    handle_path /api/* {
        reverse_proxy api:8000
    }

    handle {
        reverse_proxy web:3000
    }
}
```

- [ ] **Step 4: Add the production environment example and ignore the real file**

Create `deploy/.env.production.example`:

```dotenv
POSTGRES_DB=exposure
POSTGRES_USER=exposure
POSTGRES_PASSWORD=
ARK_API_KEY=
ARK_MODEL=doubao-seed-2-0-lite-260215
AMAP_KEY=
TENCENT_MAP_KEY=
AUTH_USERNAME=tester
AUTH_PASSWORD_HASH=
```

Append this exact line to `.gitignore`:

```gitignore
deploy/.env.production
```

- [ ] **Step 5: Add the production Compose stack**

Create `docker-compose.prod.yml`:

```yaml
name: merchant-exposure

services:
  db:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 20
    volumes:
      - production-db:/var/lib/postgresql/data

  migrate:
    build: ./services/api
    command: ["alembic", "upgrade", "head"]
    environment: &api-environment
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      ARK_API_KEY: ${ARK_API_KEY}
      ARK_MODEL: ${ARK_MODEL}
      AMAP_KEY: ${AMAP_KEY:-}
      TENCENT_MAP_KEY: ${TENCENT_MAP_KEY:-}
    depends_on:
      db:
        condition: service_healthy
    restart: "no"

  api:
    build: ./services/api
    restart: unless-stopped
    environment: *api-environment
    depends_on:
      migrate:
        condition: service_completed_successfully
    expose:
      - "8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
      interval: 10s
      timeout: 3s
      retries: 12

  worker:
    build: ./services/api
    command: ["python", "-m", "app.scans.worker"]
    restart: unless-stopped
    environment: *api-environment
    depends_on:
      migrate:
        condition: service_completed_successfully

  web:
    build: ./apps/web
    restart: unless-stopped
    environment:
      API_BASE_URL: http://api:8000
    depends_on:
      api:
        condition: service_healthy
    expose:
      - "3000"
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('http://127.0.0.1:3000').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]
      interval: 10s
      timeout: 3s
      retries: 12

  gateway:
    image: caddy:2-alpine
    restart: unless-stopped
    environment:
      AUTH_USERNAME: ${AUTH_USERNAME}
      AUTH_PASSWORD_HASH: ${AUTH_PASSWORD_HASH}
    depends_on:
      web:
        condition: service_healthy
    expose:
      - "80"
    volumes:
      - ./deploy/Caddyfile:/etc/caddy/Caddyfile:ro

  tunnel:
    image: cloudflare/cloudflared:latest
    command: ["tunnel", "--no-autoupdate", "--url", "http://gateway:80"]
    restart: unless-stopped
    depends_on:
      - gateway

volumes:
  production-db:
```

- [ ] **Step 6: Validate the stack contract and resolved Compose model**

Copy the example only for local validation, leave secret values non-production, then run:

```powershell
Copy-Item deploy/.env.production.example deploy/.env.production
$env:POSTGRES_PASSWORD = "compose-check-only"
$env:AUTH_PASSWORD_HASH = '$2a$14$composecheckcomposecheckcomposecheckcomposecheckcompose'
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml config --quiet
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_production_stack.py -q
```

Expected: Compose validation exits 0 and all stack tests PASS. Remove only the local `deploy/.env.production` validation copy after confirming its resolved absolute path is inside this repository.

- [ ] **Step 7: Commit the production stack**

```powershell
git add docker-compose.prod.yml deploy/Caddyfile deploy/.env.production.example .gitignore services/api/tests/test_production_stack.py
git commit -m "feat: add password protected production stack"
```

---

### Task 4: Add safe environment initialization and operator instructions

**Files:**
- Create: `scripts/init-prod-env.sh`
- Create: `services/api/tests/test_prod_env_script.py`
- Create: `docs/deployment/quick-tunnel.md`
- Modify: `README.md`

**Interfaces:**
- Produces: `scripts/init-prod-env.sh [output-path]`, which prompts locally on the server, generates a URL-safe PostgreSQL password and a Caddy password hash, writes mode-600 environment data, and refuses to overwrite an existing file.
- Produces: operator commands that start the stack and extract the current `trycloudflare.com` URL from tunnel logs.

- [ ] **Step 1: Write the failing environment-script contract test**

Create `services/api/tests/test_prod_env_script.py`:

```python
from pathlib import Path


ROOT = Path(__file__).parents[3]


def test_environment_initializer_protects_secrets() -> None:
    script = (ROOT / "scripts" / "init-prod-env.sh").read_text(encoding="utf-8")

    assert "umask 077" in script
    assert "openssl rand -hex 24" in script
    assert "read -r auth_password" in script
    assert "stty -echo" in script
    assert "caddy hash-password" in script
    assert "chmod 600" in script
    assert "already exists" in script
    assert "Shared passwords do not match" in script
    assert "--plaintext" not in script
```

- [ ] **Step 2: Run the script test and verify the missing-file failure**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_prod_env_script.py -q
```

Expected: FAIL because `scripts/init-prod-env.sh` does not exist.

- [ ] **Step 3: Implement the server-side environment initializer**

Create `scripts/init-prod-env.sh`:

```sh
#!/usr/bin/env sh
set -eu
umask 077

output_path="${1:-deploy/.env.production}"
if [ -e "$output_path" ]; then
    echo "$output_path already exists; refusing to overwrite it." >&2
    exit 1
fi

printf "Shared username [tester]: "
read -r auth_username
auth_username="${auth_username:-tester}"
case "$auth_username" in
    *[!A-Za-z0-9._-]*)
        echo "Shared username may contain only letters, numbers, dot, underscore, and hyphen." >&2
        exit 1
        ;;
esac
printf "Shared password: "
stty -echo
trap 'stty echo' EXIT INT TERM
read -r auth_password
stty echo
trap - EXIT INT TERM
printf "\n"
if [ -z "$auth_password" ]; then
    echo "Shared password cannot be empty." >&2
    exit 1
fi
printf "Confirm shared password: "
stty -echo
trap 'stty echo' EXIT INT TERM
read -r auth_password_confirm
stty echo
trap - EXIT INT TERM
printf "\n"
if [ "$auth_password" != "$auth_password_confirm" ]; then
    echo "Shared passwords do not match." >&2
    exit 1
fi
unset auth_password_confirm

auth_hash="$(printf "%s" "$auth_password" | docker run --rm -i caddy:2-alpine caddy hash-password)"
unset auth_password
postgres_password="$(openssl rand -hex 24)"

printf "Doubao ARK API key (leave empty to configure later): "
stty -echo
trap 'stty echo' EXIT INT TERM
read -r ark_api_key
stty echo
trap - EXIT INT TERM
printf "\n"

{
    printf "POSTGRES_DB=exposure\n"
    printf "POSTGRES_USER=exposure\n"
    printf "POSTGRES_PASSWORD=%s\n" "$postgres_password"
    printf "ARK_API_KEY=%s\n" "$ark_api_key"
    printf "ARK_MODEL=doubao-seed-2-0-lite-260215\n"
    printf "AMAP_KEY=\n"
    printf "TENCENT_MAP_KEY=\n"
    printf "AUTH_USERNAME=%s\n" "$auth_username"
    printf "AUTH_PASSWORD_HASH='%s'\n" "$auth_hash"
} > "$output_path"
chmod 600 "$output_path"
echo "Created $output_path with permissions 600."
```

- [ ] **Step 4: Write the deployment guide with exact commands**

Create `docs/deployment/quick-tunnel.md` with these sections and commands:

````markdown
# 云服务器免域名测试部署

## 前提

- Ubuntu 24.04 云服务器
- Docker、Docker Compose、Git 和 OpenSSL 已安装
- 项目位于 `~/nine`
- 服务器防火墙无需开放 3000、8000 或 5432

## 初始化秘密配置

在项目根目录执行：

```bash
chmod +x scripts/init-prod-env.sh
./scripts/init-prod-env.sh
```

共享密码和 API Key 只在服务器终端输入，不发送给他人，不截图。

## 构建并启动

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps
```

## 获取访问地址

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs tunnel | grep -o 'https://[^ ]*trycloudflare.com' | tail -n 1
```

把输出的 HTTPS 地址和共享用户名、密码分别发送给测试者。

## 检查状态

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs --tail 100 api worker web gateway tunnel
```

## 更新应用

```bash
git pull --ff-only
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d --build
```

更新后再次读取 tunnel 日志；如果地址变化，重新通知测试者。

## 停止应用

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml down
```

不要添加 `-v`，否则会删除 PostgreSQL 数据卷。
````

- [ ] **Step 5: Link the deployment guide from README**

Add a short “云端测试部署” subsection to `README.md` that links to `docs/deployment/quick-tunnel.md` and states that the existing `docker-compose.yml` remains development-only.

- [ ] **Step 6: Run the focused script test**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest tests/test_prod_env_script.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the deployment workflow**

```powershell
git add scripts/init-prod-env.sh services/api/tests/test_prod_env_script.py docs/deployment/quick-tunnel.md README.md
git commit -m "docs: add quick tunnel deployment workflow"
```

---

### Task 5: Verify the complete deployment package

**Files:**
- Modify only if verification reveals a defect in files from Tasks 1–4.

**Interfaces:**
- Consumes: all production images, Compose services, gateway routes, secret initialization, and operator documentation from Tasks 1–4.
- Produces: evidence that the package builds, tests pass, secrets remain untracked, and the Compose model exposes no internal service ports.

- [ ] **Step 1: Run the complete web test suite once**

Run:

```powershell
cd apps/web
npm.cmd test
```

Expected: all Vitest tests PASS.

- [ ] **Step 2: Run the complete API test suite once**

Run:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all Pytest tests PASS.

- [ ] **Step 3: Validate the production Compose model and build**

Create a local ignored validation environment with non-secret test values, then run:

```powershell
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml build
```

Expected: Compose validation and all image builds exit 0.

- [ ] **Step 4: Audit the resolved port exposure and tracked secrets**

Run:

```powershell
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml config
git status --short
git ls-files deploy/.env.production services/api/.env
```

Expected: the resolved Compose output contains no host `ports` entries for `3000`, `8000`, or `5432`; neither real environment file is tracked; unrelated pre-existing working-tree changes remain untouched.

- [ ] **Step 5: Remove only the ignored local validation environment**

Resolve `deploy/.env.production`, verify that it is inside the repository's `deploy` directory, and delete that one validation file. Do not remove any server environment file or Docker volume.

- [ ] **Step 6: Commit verification fixes only if files changed**

If verification required a code/config correction, stage only those corrected files and commit:

```powershell
git commit -m "fix: complete production deployment verification"
```

If no file changed, do not create an empty commit.

- [ ] **Step 7: Prepare the server handoff without publishing yet**

Record the exact commit SHA to deploy:

```powershell
git rev-parse HEAD
git status -sb
```

Before pushing to GitHub or changing the cloud server, ask the user for explicit confirmation because both operations change external state. After authorization, push once, verify the remote branch HEAD once, then guide the user through the commands in `docs/deployment/quick-tunnel.md`.

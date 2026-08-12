import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "@playwright/test";

const webRoot = path.dirname(fileURLToPath(import.meta.url));
const apiRoot = path.resolve(webRoot, "../../services/api");
const python = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";

const managedServers = [
  {
    command: `${python} -m scripts.demo_server`,
    cwd: apiRoot,
    url: "http://127.0.0.1:8000/health",
    reuseExistingServer: true,
    timeout: 60_000,
  },
  {
    command: "npm run dev -- --hostname 127.0.0.1",
    cwd: webRoot,
    env: { NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000" },
    url: "http://127.0.0.1:3000",
    reuseExistingServer: true,
    timeout: 60_000,
  },
];

export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://127.0.0.1:3000" },
  webServer: process.env.PLAYWRIGHT_EXTERNAL_SERVERS ? undefined : managedServers,
});

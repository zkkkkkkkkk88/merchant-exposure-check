import { afterEach, describe, expect, it, vi } from "vitest";
import { unstable_doesMiddlewareMatch } from "next/experimental/testing/server";
import { NextRequest } from "next/server";
import { render, screen } from "@testing-library/react";

const cryptoSpies = vi.hoisted(() => ({ scryptSync: vi.fn() }));

vi.mock("node:crypto", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:crypto")>();
  cryptoSpies.scryptSync.mockImplementation(actual.scryptSync);
  return {
    ...actual,
    default: { ...actual, scryptSync: cryptoSpies.scryptSync },
    scryptSync: cryptoSpies.scryptSync,
  };
});

import LoginPage from "@/app/login/page";
import { POST as login } from "@/app/api/access/login/route";
import { POST as logout } from "@/app/api/access/logout/route";
import { createAccessSession, verifyAccessSession } from "@/lib/access-session";
import {
  accessDecisionForPath,
  config,
  proxy,
} from "@/proxy";

const SECRET = "proxy-test-session-secret";
const DEMO_HASH = "scrypt$00112233445566778899aabbccddeeff$99f5251cf1506e7f2387aa6c3eea5395a235801b1834e4e0e75e6bdb8531c832bc4e491e4735a8b4f8e550f31d966c9e622e9372ebf3d834e7ba9aa41c3de332";
const ADMIN_HASH = "scrypt$ffeeddccbbaa99887766554433221100$1f22900a6ff17b05cb0ffa66f401d70792ba4ed215f1393eab3bef87deee4613c2b1b7390f3091a1b8af035af0f44201414c194b5f226ea140f464d55163c52a";

afterEach(() => {
  cryptoSpies.scryptSync.mockClear();
  delete process.env.ACCESS_AUTH_REQUIRED;
  delete process.env.ACCESS_SESSION_SECRET;
  delete process.env.ACCESS_ADMIN_USERNAME;
  delete process.env.ACCESS_ADMIN_PASSWORD_HASH;
  delete process.env.ACCESS_DEMO_USERNAME;
  delete process.env.ACCESS_DEMO_PASSWORD_HASH;
});

function loginRequest(username: string, password: string): NextRequest {
  return new NextRequest("http://localhost/api/access/login", {
    method: "POST",
    body: new URLSearchParams({ username, password }),
    headers: { "content-type": "application/x-www-form-urlencoded" },
  });
}

function configureCredentials(): void {
  process.env.ACCESS_SESSION_SECRET = SECRET;
  process.env.ACCESS_ADMIN_USERNAME = "owner";
  process.env.ACCESS_ADMIN_PASSWORD_HASH = ADMIN_HASH;
  process.env.ACCESS_DEMO_USERNAME = "visitor";
  process.env.ACCESS_DEMO_PASSWORD_HASH = DEMO_HASH;
}

describe("proxy access decisions", () => {
  it.each([
    "/login",
    "/login/",
    "/api/access/login",
    "/_next/static/chunks/app.js",
    "/_next/image",
    "/favicon.ico",
  ])("allows the public path %s without a session", (pathname) => {
    expect(accessDecisionForPath(pathname, true, null)).toEqual({ action: "public" });
  });

  it("requires a verified session for logout", () => {
    expect(accessDecisionForPath("/api/access/logout", true, null)).toEqual({ action: "login" });
    expect(accessDecisionForPath("/api/access/logout", true, "demo")).toEqual({
      action: "allow",
      role: "demo",
    });
  });

  it("defaults to admin when authentication is disabled", () => {
    expect(accessDecisionForPath("/reports/scan-1", false, null)).toEqual({
      action: "allow",
      role: "admin",
    });
  });

  it("requires login when authentication is enabled without a role", () => {
    expect(accessDecisionForPath("/merchants", true, null)).toEqual({ action: "login" });
  });

  it("does not make a Server Action POST to the login page public", () => {
    expect(accessDecisionForPath("/login", true, null, "POST", true)).toEqual({
      action: "login",
    });
  });

  it.each(["admin", "demo"] as const)("allows the verified %s role", (role) => {
    expect(accessDecisionForPath("/queries", true, role)).toEqual({
      action: "allow",
      role,
    });
  });
});

describe("proxy integration", () => {
  it("matches ordinary pages and the page POSTs used by Server Actions", () => {
    expect(unstable_doesMiddlewareMatch({ config, nextConfig: {}, url: "/methodology" })).toBe(true);
    expect(unstable_doesMiddlewareMatch({
      config,
      nextConfig: {},
      url: "/queries",
      headers: { "next-action": "action-id" },
    })).toBe(true);
  });

  it.each(["/_next/static/app.js", "/_next/image?url=%2Flogo.png", "/favicon.ico"])(
    "does not match the static path %s",
    (url) => {
      expect(unstable_doesMiddlewareMatch({ config, nextConfig: {}, url })).toBe(false);
    },
  );

  it("redirects an unauthenticated protected request to login", async () => {
    process.env.ACCESS_AUTH_REQUIRED = "true";
    process.env.ACCESS_SESSION_SECRET = SECRET;

    const response = await proxy(new NextRequest("http://localhost/merchants"));

    expect(response.headers.get("location")).toBe("http://localhost/login");
  });

  it("does not dispatch an unauthenticated Server Action POST from the login page", async () => {
    process.env.ACCESS_AUTH_REQUIRED = "true";
    process.env.ACCESS_SESSION_SECRET = SECRET;
    const request = new NextRequest("http://localhost/login", {
      method: "POST",
      body: "action-payload",
      headers: { "next-action": "mutating-action-id" },
    });

    const response = await proxy(request);

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe("http://localhost/login");
    expect(response.headers.get("x-middleware-next")).not.toBe("1");
  });

  it("replaces an incoming role header with the verified demo role", async () => {
    process.env.ACCESS_AUTH_REQUIRED = "true";
    process.env.ACCESS_SESSION_SECRET = SECRET;
    const session = await createAccessSession("demo", SECRET);
    const request = new NextRequest("http://localhost/queries", {
      headers: {
        cookie: `access_session=${session}`,
        "x-access-role": "admin",
      },
    });

    const response = await proxy(request);

    expect(response.headers.get("x-middleware-request-x-access-role")).toBe("demo");
  });

  it("preserves filters when restoring merchant context after authentication", async () => {
    const request = new NextRequest("http://localhost/platform-audits?view=missing", {
      headers: { cookie: "merchant_context=merchant-1" },
    });

    const response = await proxy(request);

    expect(response.headers.get("location")).toBe(
      "http://localhost/platform-audits?view=missing&merchant=merchant-1",
    );
  });
});

describe("access Route Handlers", () => {
  it.each([
    ["owner", "管理员密码-456", "admin"],
    ["visitor", "演示密码-123", "demo"],
  ] as const)("creates a 12-hour %s session for valid credentials", async (username, password, role) => {
    configureCredentials();

    const response = await login(loginRequest(username, password));
    const cookie = response.headers.get("set-cookie") ?? "";
    const session = /access_session=([^;]+)/.exec(cookie)?.[1];

    expect(response.headers.get("location")).toBe("http://localhost/");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("SameSite=lax");
    expect(cookie).toContain("Path=/");
    expect(cookie).toContain("Max-Age=43200");
    await expect(verifyAccessSession(session ?? "", SECRET)).resolves.toBe(role);
  });

  it("returns the same neutral redirect for an unknown username or wrong password", async () => {
    configureCredentials();

    const unknown = await login(loginRequest("unknown", "演示密码-123"));
    const wrongPassword = await login(loginRequest("visitor", "wrong"));

    expect(unknown.headers.get("location")).toBe("http://localhost/login?error=invalid");
    expect(wrongPassword.headers.get("location")).toBe("http://localhost/login?error=invalid");
    expect(unknown.headers.get("set-cookie")).toBeNull();
    expect(wrongPassword.headers.get("set-cookie")).toBeNull();
  });

  it("performs one scrypt verification for unknown and known usernames", async () => {
    configureCredentials();

    await login(loginRequest("unknown", "演示密码-123"));

    expect(cryptoSpies.scryptSync).toHaveBeenCalledOnce();
    expect(Buffer.from(cryptoSpies.scryptSync.mock.calls[0][1]).toString("hex")).toBe("00".repeat(16));
    expect(cryptoSpies.scryptSync.mock.calls[0][2]).toBe(64);

    cryptoSpies.scryptSync.mockClear();
    await login(loginRequest("visitor", "wrong"));

    expect(cryptoSpies.scryptSync).toHaveBeenCalledOnce();
  });

  it("performs one dummy scrypt verification when a credential field is missing", async () => {
    configureCredentials();
    const request = new NextRequest("http://localhost/api/access/login", {
      method: "POST",
      body: new URLSearchParams({ password: "演示密码-123" }),
      headers: { "content-type": "application/x-www-form-urlencoded" },
    });

    const response = await login(request);

    expect(cryptoSpies.scryptSync).toHaveBeenCalledOnce();
    expect(response.headers.get("location")).toBe("http://localhost/login?error=invalid");
  });

  it("fails closed when the session secret is missing", async () => {
    configureCredentials();
    delete process.env.ACCESS_SESSION_SECRET;

    const response = await login(loginRequest("visitor", "演示密码-123"));

    expect(response.headers.get("location")).toBe("http://localhost/login?error=invalid");
    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("deletes only the access session on logout", async () => {
    const response = await logout(new NextRequest("http://localhost/api/access/logout", {
      method: "POST",
      headers: { cookie: "access_session=value; merchant_context=merchant-1" },
    }));
    const cookie = response.headers.get("set-cookie") ?? "";

    expect(response.headers.get("location")).toBe("http://localhost/login");
    expect(cookie).toContain("access_session=");
    expect(cookie).not.toContain("merchant_context");
  });
});

describe("login page", () => {
  it("posts both credentials and shows a neutral error", async () => {
    render(await LoginPage({ searchParams: Promise.resolve({ error: "invalid" }) }));

    expect(screen.getByRole("textbox", { name: "用户名" })).toHaveAttribute("name", "username");
    expect(screen.getByLabelText("密码")).toHaveAttribute("name", "password");
    expect(screen.getByRole("form")).toHaveAttribute("action", "/api/access/login");
    expect(screen.getByText("用户名或密码不正确，请重试。")).toBeInTheDocument();
    expect(screen.getByText(/项目所有者提供的访问凭据/)).toBeInTheDocument();
  });
});

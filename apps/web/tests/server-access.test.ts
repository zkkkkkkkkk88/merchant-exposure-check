import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { headersMock } = vi.hoisted(() => ({
  headersMock: vi.fn(),
}));

vi.mock("next/headers", () => ({ headers: headersMock }));

import {
  AccessAuthenticationError,
  DemoReadOnlyError,
  getServerAccessRole,
  requireServerAdmin,
  trustedApiHeaders,
} from "@/lib/server-access";
import {
  createMerchantAction,
  getJourneyProgressAction,
} from "@/app/server-actions";

describe("server access role propagation", () => {
  beforeEach(() => {
    headersMock.mockResolvedValue(new Headers({ "x-access-role": "admin" }));
    process.env.ACCESS_AUTH_REQUIRED = "true";
    process.env.INTERNAL_API_SECRET = "server-internal-secret";
    process.env.NEXT_PUBLIC_INTERNAL_API_SECRET = "must-not-be-used";
  });

  afterEach(() => {
    headersMock.mockReset();
    delete process.env.ACCESS_AUTH_REQUIRED;
    delete process.env.INTERNAL_API_SECRET;
    delete process.env.NEXT_PUBLIC_INTERNAL_API_SECRET;
  });

  it("builds admin API headers from the proxy role and server-only secret", async () => {
    const result = await trustedApiHeaders({
      "content-type": "application/json",
      "x-access-role": "demo",
      "x-internal-auth": "caller-controlled",
    });

    expect(result.get("content-type")).toBe("application/json");
    expect(result.get("x-access-role")).toBe("admin");
    expect(result.get("x-internal-auth")).toBe("server-internal-secret");
    expect(result.get("x-internal-auth")).not.toBe(process.env.NEXT_PUBLIC_INTERNAL_API_SECRET);
  });

  it("preserves a demo role for server-side read calls", async () => {
    headersMock.mockResolvedValue(new Headers({ "x-access-role": "demo" }));

    await expect(getServerAccessRole()).resolves.toBe("demo");
  });

  it("rejects demo mutations with the dedicated read-only error", async () => {
    headersMock.mockResolvedValue(new Headers({ "x-access-role": "demo" }));

    await expect(requireServerAdmin()).rejects.toBeInstanceOf(DemoReadOnlyError);
  });

  it("defaults to admin only while access authentication is disabled", async () => {
    delete process.env.ACCESS_AUTH_REQUIRED;
    headersMock.mockResolvedValue(new Headers());

    await expect(getServerAccessRole()).resolves.toBe("admin");
  });

  it("rejects a missing trusted role while access authentication is required", async () => {
    headersMock.mockResolvedValue(new Headers());

    await expect(getServerAccessRole()).rejects.toBeInstanceOf(AccessAuthenticationError);
  });

  it("keeps merchant creation behind an admin Server Action", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "merchant-1" }), {
      status: 201,
      headers: { "content-type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(createMerchantAction({
      name: "测试商家",
      branch_name: null,
      city: "杭州",
      district: null,
      industry: "餐饮",
      address: null,
      price_range: null,
      opening_hours: null,
      products: [],
      strengths: [],
      sources: [],
    })).resolves.toEqual({ id: "merchant-1" });

    const requestHeaders = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(requestHeaders.get("x-access-role")).toBe("admin");
    expect(requestHeaders.get("x-internal-auth")).toBe("server-internal-secret");
  });

  it("keeps demo journey reads behind a role-propagating Server Action", async () => {
    headersMock.mockResolvedValue(new Headers({ "x-access-role": "demo" }));
    const payload = { current_step: "profile", completed_count: 0, total_count: 6, steps: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "content-type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getJourneyProgressAction("merchant-1")).resolves.toEqual(payload);

    const requestHeaders = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(requestHeaders.get("x-access-role")).toBe("demo");
  });
});

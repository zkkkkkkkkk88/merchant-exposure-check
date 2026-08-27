import { afterEach, beforeEach, expect, it, vi } from "vitest";

const { headersMock } = vi.hoisted(() => ({ headersMock: vi.fn() }));

vi.mock("next/headers", () => ({ headers: headersMock }));

import {
  parseProfileAction,
  saveProfileAction,
  saveProfileAndGenerateAction,
} from "@/app/merchants/[id]/actions";
import { DemoReadOnlyError } from "@/lib/server-access";

const facts = [
  { field_key: "location.city", value: "云南", confirmation_status: "confirmed" as const, source_urls: [] },
  { field_key: "category.precise", value: "口腔门诊", confirmation_status: "confirmed" as const, source_urls: [] },
];

beforeEach(() => {
  headersMock.mockResolvedValue(new Headers({ "x-access-role": "admin" }));
  process.env.ACCESS_AUTH_REQUIRED = "true";
  process.env.INTERNAL_API_SECRET = "test-internal-secret";
});

afterEach(() => {
  headersMock.mockReset();
  delete process.env.ACCESS_AUTH_REQUIRED;
  delete process.env.INTERNAL_API_SECRET;
  vi.unstubAllGlobals();
});

it("saves the edited profile through a server action", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ merchant_id: "m1", facts }), {
    status: 200,
    headers: { "content-type": "application/json" },
  }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(saveProfileAction("m1", facts)).resolves.toMatchObject({ ok: true });
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/merchants/m1/profile",
    expect.objectContaining({ method: "PUT", body: JSON.stringify({ facts }) }),
  );
  const requestHeaders = fetchMock.mock.calls[0][1]?.headers as Headers;
  expect(requestHeaders.get("x-access-role")).toBe("admin");
  expect(requestHeaders.get("x-internal-auth")).toBe("test-internal-secret");
});

it("saves first and then creates a new query set from the edited profile", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ merchant_id: "m1", facts }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ id: "set2" }), { status: 201 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(saveProfileAndGenerateAction("m1", facts)).resolves.toEqual({ ok: true, data: { id: "set2" } });
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock.mock.calls[0][0]).toContain("/merchants/m1/profile");
  expect(fetchMock.mock.calls[1][0]).toContain("/merchants/m1/query-sets/generate");
});

it("parses pasted profile text on the server", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ merchant_id: "m1", facts }), { status: 200 })));
  await expect(parseProfileAction("m1", "至少十个字的商家公开资料", [])).resolves.toMatchObject({ ok: true });
});

it("rejects a demo profile mutation before fetch runs", async () => {
  headersMock.mockResolvedValue(new Headers({ "x-access-role": "demo" }));
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);

  await expect(saveProfileAction("m1", facts)).rejects.toBeInstanceOf(DemoReadOnlyError);
  expect(fetchMock).not.toHaveBeenCalled();
});

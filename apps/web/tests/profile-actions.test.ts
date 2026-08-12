import { afterEach, expect, it, vi } from "vitest";

import {
  parseProfileAction,
  saveProfileAction,
  saveProfileAndGenerateAction,
} from "@/app/merchants/[id]/actions";

const facts = [
  { field_key: "location.city", value: "云南", confirmation_status: "confirmed" as const, source_urls: [] },
  { field_key: "category.precise", value: "口腔门诊", confirmation_status: "confirmed" as const, source_urls: [] },
];

afterEach(() => vi.unstubAllGlobals());

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

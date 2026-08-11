import { afterEach, describe, expect, it, vi } from "vitest";

import { createScanAction, updateQueryAction } from "@/app/queries/actions";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("query workflow server actions", () => {
  it("persists camelCase query changes with the FastAPI field names", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      id: "q1",
      query_set_id: "set1",
      text: "杭州餐饮有哪些？",
      category: "geo",
      reason: "地域发现",
      priority: 1,
      review_status: "approved",
      is_enabled: true,
      created_at: "2026-08-11T00:00:00Z",
      updated_at: "2026-08-11T00:01:00Z",
    }), { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await updateQueryAction("q1", {
      reviewStatus: "approved",
      isEnabled: true,
    });

    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/queries/q1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ review_status: "approved", is_enabled: true }),
      }),
    );
  });

  it("creates an Ark scan without waiting for model results", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      id: "scan1",
      merchant_id: "m1",
      query_set_id: "set1",
      adapter_name: "ark",
      status: "queued",
      success_count: 0,
      failure_count: 0,
      error_summary: null,
      created_at: "2026-08-11T00:00:00Z",
      started_at: null,
      finished_at: null,
      results: [],
    }), { status: 201, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await createScanAction("m1", "set1");

    expect(result).toMatchObject({ ok: true, data: { id: "scan1", status: "queued" } });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/scan-runs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ merchant_id: "m1", query_set_id: "set1", adapter_name: "ark" }),
      }),
    );
  });

  it("turns a no-approved-query conflict into a readable action error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: "No approved and enabled queries" }),
      { status: 409, headers: { "content-type": "application/json" } },
    )));

    await expect(createScanAction("m1", "set1")).resolves.toEqual({
      ok: false,
      error: "当前没有已批准且启用的问题，请先审核问题库。",
    });
  });
});

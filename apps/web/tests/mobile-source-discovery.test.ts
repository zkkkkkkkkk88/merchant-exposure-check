import { afterEach, describe, expect, it, vi } from "vitest";

import { discoverMobileSources } from "@/lib/api";
import type { MobileAnswerDraft } from "@/lib/mobile-answer-parser";
import { countRecurringCompetitors, mergeConfirmedSources } from "@/lib/mobile-source-discovery";

function draft(competitors: string[]): MobileAnswerDraft {
  return {
    itemId: crypto.randomUUID(),
    mentionLevel: "none",
    competitors,
    answerExcerpt: "",
    needsReview: false,
  };
}

describe("countRecurringCompetitors", () => {
  it("keeps competitors appearing in at least two independent answers", () => {
    const result = countRecurringCompetitors(
      [
        draft(["王天佑口腔", "福康口腔", "王天佑口腔"]),
        draft(["王天佑口腔"]),
        draft(["王天佑口腔", "福康口腔", "偶发诊所", "澜沧皓雅口腔"]),
      ],
      "澜沧皓雅口腔门诊部",
    );

    expect(result).toEqual([
      { name: "王天佑口腔", occurrence_count: 3 },
      { name: "福康口腔", occurrence_count: 2 },
    ]);
  });

  it("limits the request to the three most frequent competitors", () => {
    const result = countRecurringCompetitors(
      [
        draft(["甲诊所", "乙诊所", "丙诊所", "丁诊所"]),
        draft(["甲诊所", "乙诊所", "丙诊所", "丁诊所"]),
        draft(["丁诊所"]),
      ],
      "目标诊所",
    );

    expect(result).toEqual([
      { name: "丁诊所", occurrence_count: 3 },
      { name: "甲诊所", occurrence_count: 2 },
      { name: "乙诊所", occurrence_count: 2 },
    ]);
  });
});

describe("discoverMobileSources", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts the limited discovery payload and returns source groups", async () => {
    const payload = {
      location_text: "澜沧县",
      competitors: [{ name: "王天佑口腔", occurrence_count: 2 }],
    };
    const responseBody = {
      groups: [{ entity_name: "王天佑口腔", sources: [], error: null }],
      external_call_count: 1,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(discoverMobileSources("merchant-1", payload)).resolves.toEqual(responseBody);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/merchants/merchant-1/mobile-checks/discover-sources",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      }),
    );
  });
});

describe("mergeConfirmedSources", () => {
  it("accepts checked automatic sources, merges manual entries and removes duplicate urls", () => {
    const automatic = JSON.stringify({
      entity_name: "王天佑口腔诊所",
      source_type: "recruitment",
      title: "招聘页",
      facts: ["设备"],
      url: "https://jobs.example/wty",
      evidence_kind: "third_party",
      access_status: "reference",
      reused_from_audit: false,
    });

    const result = mergeConfirmedSources(
      [automatic, "not-json"],
      [
        "王天佑口腔诊所｜招聘｜重复页面｜设备｜https://jobs.example/wty",
        "澜沧皓雅口腔门诊部｜机构介绍｜机构主页｜地址、电话｜https://merchant.example/profile",
        "无网址机构｜机构介绍｜无网址｜事实｜",
      ].join("\n"),
    );

    expect(result).toHaveLength(2);
    expect(result[0]).toMatchObject({
      title: "招聘页",
      url: "https://jobs.example/wty",
      is_confirmed: true,
    });
    expect(result[1]).toMatchObject({
      entity_name: "澜沧皓雅口腔门诊部",
      source_type: "profile",
      url: "https://merchant.example/profile",
      is_confirmed: true,
    });
  });
});

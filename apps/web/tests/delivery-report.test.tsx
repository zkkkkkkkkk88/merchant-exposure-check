import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DeliveryReportPage from "@/app/delivery-report/page";
import { PrintReportButton } from "@/components/print-report-button";
import {
  getJourneyProgress,
  getLatestPlatformAudit,
  getMerchant,
  getMerchantProfile,
  getMerchants,
  getMobileWorkspace,
  getQuerySets,
} from "@/lib/api";

vi.mock("@/components/app-shell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/components/merchant-switcher", () => ({ MerchantSwitcher: () => <div>切换商家</div> }));
vi.mock("@/lib/api", () => ({
  getJourneyProgress: vi.fn(),
  getLatestPlatformAudit: vi.fn(),
  getMerchant: vi.fn(),
  getMerchantProfile: vi.fn(),
  getMerchants: vi.fn(),
  getMobileWorkspace: vi.fn(),
  getQuerySets: vi.fn(),
}));

describe("delivery report", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getMerchants).mockResolvedValue([{ id: "m1", name: "示例口腔", branch_name: null }]);
    vi.mocked(getMerchant).mockResolvedValue({
      id: "m1", name: "示例口腔", normalized_name: "示例口腔", branch_name: null,
      city: "澜沧", district: null, industry: "口腔", address: "示例路1号", price_range: null,
      opening_hours: null, products: [], strengths: [], sources: [], created_at: "2026-08-14", updated_at: "2026-08-14",
    });
    vi.mocked(getMerchantProfile).mockResolvedValue({ merchant_id: "m1", facts: [
      { field_key: "contact.phone", value: "0879-1234567", confirmation_status: "confirmed", source_urls: ["https://example.com"] },
    ] });
    vi.mocked(getQuerySets).mockResolvedValue([]);
    vi.mocked(getJourneyProgress).mockResolvedValue({ merchant_id: "m1", completed_count: 4, total_count: 6, current_step: "action", steps: [] });
    vi.mocked(getLatestPlatformAudit).mockResolvedValue({
      id: "audit", merchant_id: "m1", status: "partial", created_at: "2026-08-14", started_at: null,
      finished_at: null, error_message: null, platforms: [
        { id: "p1", platform_key: "amap", platform_name: "高德地图", status: "incomplete", found: true, fields: {}, issues: ["营业时间缺失"], evidence: [], checked_at: "2026-08-14" },
      ],
    });
    vi.mocked(getMobileWorkspace).mockResolvedValue({
      latestRoundId: "r1", sourceRoundId: "r1",
      metrics: { confirmedCount: 3, mentionCount: 2, primaryCount: 1, categoryCoveredCount: 2, categoryTotalCount: 3, informationAccurateCount: 2, informationEvaluatedCount: 2, mentionRate: 2 / 3, primaryRate: 1 / 3, categoryCoverageRate: 2 / 3, informationAccuracyRate: 1, sourceCoverageRate: 0.5 },
      entities: ["示例口腔", "同行甲", "同行乙"], sourceGaps: [],
      latestRoundAnswers: [{ position: 1, question: "澜沧有哪些民营口腔？", answer: "推荐示例口腔和同行甲。", mentionLevel: "primary", mentionLabel: "首批推荐", targetPosition: 1 }],
      recommendationPlaybook: {
        diagnosis: { summary: "目标商家已进入首批推荐。", mentionedCount: 2, totalCount: 3, questions: [] },
        competitorReasons: [
          { name: "同行甲", questionCount: 2, reasons: [{ text: "设备和服务项目描述清楚", questionPositions: [1, 2], confidence: "answer_only" }] },
          { name: "同行乙", questionCount: 1, reasons: [] },
        ],
        actions: [{ key: "facts", title: "补齐可核验服务事实", why: "提高公开信息清晰度", steps: ["核实服务项目"], materials: ["项目清单"], publishTargets: [{ priority: 1, channel: "地图商户页", content: "补充服务项目" }], linkEntryHint: "发布后保存链接", examples: [], completionCriteria: "页面可公开访问", confidence: "answer_only" }],
        comparison: { previousRoundId: "r0", currentRoundId: "r1", mentionRateBefore: 0, mentionRateAfter: 2 / 3, primaryRateBefore: 0, primaryRateAfter: 1 / 3, questions: [] },
        disclaimer: "答案来自实测，不代表豆包官方排序规则。",
      },
    });
  });

  it("aggregates evidence, repeated competitors, gaps and next actions", async () => {
    render(await DeliveryReportPage({ searchParams: Promise.resolve({ merchant: "m1" }) }));

    expect(screen.getByRole("heading", { name: "手机版豆包商家可见性交付报告" })).toBeVisible();
    expect(screen.getByText("至少首批推荐一次")).toBeVisible();
    expect(screen.getByText("是", { selector: "strong" })).toBeVisible();
    expect(screen.getByText("推荐示例口腔和同行甲。")).toBeVisible();
    expect(screen.getByRole("heading", { name: "同行甲" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "同行乙" })).not.toBeInTheDocument();
    expect(screen.getByText("营业时间缺失")).toBeVisible();
    expect(screen.getByRole("heading", { name: "补齐可核验服务事实" })).toBeVisible();
    expect(screen.getByText("0% → 67%")).toBeVisible();
    expect(screen.getByText("答案来自实测，不代表豆包官方排序规则。")).toBeVisible();
  });

  it("prints through the browser so the user can save PDF", () => {
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    render(<PrintReportButton />);
    fireEvent.click(screen.getByRole("button", { name: "打印 / 另存为 PDF" }));
    expect(print).toHaveBeenCalledOnce();
    print.mockRestore();
  });
});

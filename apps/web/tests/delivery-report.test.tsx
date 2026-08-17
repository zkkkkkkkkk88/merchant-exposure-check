import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DeliveryReportPage from "@/app/delivery-report/page";
import { PrintReportButton } from "@/components/print-report-button";
import {
  getDashboard,
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
  getDashboard: vi.fn(),
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
      { field_key: "location.city", value: "云南", confirmation_status: "confirmed", source_urls: [] },
    ] });
    vi.mocked(getDashboard).mockResolvedValue({
      merchant: { id: "m1", name: "示例口腔" },
      lastRunAt: "2026-08-14",
      metrics: {
        mentionRate: 1, visibilityStage: "mentioned", readinessScore: 0.8,
        profileCompleteness: 0.8, publicVerifiability: 0.7, highIntentHitRate: 0.6,
        competitorGapClosure: 0.5, sourceCoverageRate: 0.7, validQueryCount: 3, totalQueryCount: 3,
      },
      trend: [], categories: [], competitors: [],
      actions: [{
        id: "coverage-category", title: "统一精准品类信息", priority: "high", evidenceCount: 3,
        description: "相关问题需要统一品类表述。", steps: ["核对规范品类"], channels: ["地图商户页"],
        materials: ["执业许可"], example: "示例表述", completionCriteria: "两个公开页面信息一致。",
        questions: ["示例问题"],
        sourceChannels: [{ domain: "m.map.360.cn", citationCount: 2, access: "submission", label: "需要认领或纠错" }],
      }],
    });
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
      metrics: { confirmedCount: 3, mentionCount: 3, primaryCount: 0, categoryCoveredCount: 2, categoryTotalCount: 3, informationAccurateCount: 2, informationEvaluatedCount: 3, mentionRate: 1, primaryRate: 0, categoryCoverageRate: 2 / 3, informationAccuracyRate: 2 / 3, sourceCoverageRate: 0.5 },
      entities: ["示例口腔", "同行甲", "同行乙"], sourceGaps: [],
      latestRoundAnswers: [
        { position: 1, question: "澜沧有哪些民营口腔？", answer: "第一份完整原始回答。", mentionLevel: "supplementary", mentionLabel: "补充提及", targetPosition: 6 },
        { position: 2, question: "澜沧有哪些洁牙机构？", answer: "第二份完整原始回答。", mentionLevel: "supplementary", mentionLabel: "补充提及", targetPosition: 4 },
        { position: 3, question: "澜沧有哪些舒适口腔？", answer: "第三份完整原始回答。", mentionLevel: "supplementary", mentionLabel: "补充提及", targetPosition: 3 },
      ],
      channelMaintenance: {
        citedChannels: [{
          domain: "m.jobui.com",
          citationCount: 1,
          access: "maintainable",
          accessLabel: "可直接维护",
          sourceTypes: ["招聘或企业主页"],
          links: [{ title: "企业主页", url: "https://m.jobui.com/company/1" }],
        }],
        candidateChannels: [{ channel: "机构官网", content: "发布完整机构介绍" }],
      },
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
    expect(screen.getByText("可见性等级")).toBeVisible();
    expect(screen.getByText("稳定可见", { selector: "strong" })).toBeVisible();
    expect(screen.getByText("补充提及 · 第 6 位")).toBeVisible();
    expect(screen.getByText("第一份完整原始回答。")).not.toBeVisible();
    fireEvent.click(screen.getByText(/Q1 · 澜沧有哪些民营口腔？ · 补充提及 · 第 6 位/));
    expect(screen.getByText("第一份完整原始回答。")).toBeVisible();
    expect(screen.getByRole("heading", { name: "同行甲" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "同行乙" })).not.toBeInTheDocument();
    expect(screen.getByText("营业时间缺失")).toBeVisible();
    expect(screen.getByRole("heading", { name: "公开信息渠道维护清单" })).toBeVisible();
    expect(screen.getByText("m.map.360.cn")).toBeVisible();
    expect(screen.getByText("引用 2 次 · 检测回答引用来源")).toBeVisible();
    expect(screen.getByText("需要认领或纠错")).toBeVisible();
    expect(screen.getByText("m.jobui.com")).toBeVisible();
    expect(screen.getByRole("link", { name: "企业主页" })).toHaveAttribute("href", "https://m.jobui.com/company/1");
    expect(screen.getByText("机构官网")).toBeVisible();
    expect(screen.getByText("发布完整机构介绍")).toBeVisible();
    expect(screen.getByText(/不保证进入首批推荐/)).toBeVisible();
    expect(screen.getByRole("heading", { name: "补齐可核验服务事实" })).toBeVisible();
    expect(screen.getByText("0% → 67%")).toBeVisible();
    expect(screen.getByText("答案来自实测，不代表豆包官方排序规则。")).toBeVisible();
    expect(screen.getByText("联系电话")).toBeVisible();
    expect(screen.getByText("省份 / 城市")).toBeVisible();
    expect(screen.queryByText("contact.phone")).not.toBeInTheDocument();
    expect(screen.queryByText("location.city")).not.toBeInTheDocument();
    expect(screen.getByText("核心检测已完成")).toBeVisible();
    expect(screen.getByRole("button", { name: "打印 / 另存为 PDF" })).toBeEnabled();
  });

  it("prints through the browser so the user can save PDF", () => {
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    render(<PrintReportButton />);
    fireEvent.click(screen.getByRole("button", { name: "打印 / 另存为 PDF" }));
    expect(print).toHaveBeenCalledOnce();
    print.mockRestore();
  });

  it("does not print an incomplete report", () => {
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    render(<PrintReportButton disabled disabledReason="手机实测需要确认完整的3道回答" />);
    const button = screen.getByRole("button", { name: "打印 / 另存为 PDF" });
    expect(button).toBeDisabled();
    expect(screen.getByText("手机实测需要确认完整的3道回答")).toBeVisible();
    fireEvent.click(button);
    expect(print).not.toHaveBeenCalled();
    print.mockRestore();
  });
});

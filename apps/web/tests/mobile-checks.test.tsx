import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MobileChecksPage from "@/app/mobile-checks/page";
import { getMerchants, getMobileWorkspace, getMobileValidationSets, getQuerySets } from "@/lib/api";

vi.mock("next/navigation", () => ({
  usePathname: () => "/mobile-checks",
  useSearchParams: () => new URLSearchParams("merchant=merchant-1"),
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getMerchants: vi.fn(),
  getMobileWorkspace: vi.fn(),
  getMobileValidationSets: vi.fn(),
  getQuerySets: vi.fn(),
  getJourneyProgress: vi.fn().mockResolvedValue(null),
}));

describe("mobile Doubao workspace", () => {
  beforeEach(() => { vi.clearAllMocks(); vi.mocked(getQuerySets).mockResolvedValue([]); });

  it("requires an explicit merchant instead of selecting the first one", async () => {
    vi.mocked(getMerchants).mockResolvedValue([{ id: "merchant-1", name: "澜沧皓雅口腔门诊部", branch_name: null }]);

    render(await MobileChecksPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("heading", { name: "请先选择目标商家" })).toBeInTheDocument();
    expect(getMobileValidationSets).not.toHaveBeenCalled();
    expect(getMobileWorkspace).not.toHaveBeenCalled();
  });

  it("shows the three-dialog one-paste workflow", async () => {
    vi.mocked(getMerchants).mockResolvedValue([{ id: "merchant-1", name: "澜沧舒适口腔", branch_name: null }]);
    vi.mocked(getMobileValidationSets).mockResolvedValue([{ id: "set-1", merchant_id: "merchant-1", created_at: "2026-08-12T00:00:00Z", items: [
      { id: "item-1", query_id: "query-1", position: 1, query: { id: "query-1", query_set_id: "qs", text: "澜沧县口碑好的口腔机构有哪些？", category: "geo", reason: "泛推荐", priority: 1, intent_type: "recommendation", fact_keys: [], review_status: "approved", is_enabled: true, created_at: "2026-08-12T00:00:00Z", updated_at: "2026-08-12T00:00:00Z" } },
    ] }]);
    vi.mocked(getMobileWorkspace).mockResolvedValue({ latestRoundId: null, sourceRoundId: null, metrics: null, entities: ["澜沧舒适口腔"], sourceGaps: [] });
    vi.mocked(getQuerySets).mockResolvedValue([{ id: "qs", merchant_id: "merchant-1", version: 1, generator_name: "oral-private-v1", created_at: "2026-08-12T00:00:00Z", queries: Array.from({ length: 15 }, (_, index) => ({ id: `candidate-${index}`, query_set_id: "qs", text: `民营口腔候选问题 ${index + 1}`, category: index % 2 ? "geo" : "category", reason: "候选", priority: 1, intent_type: "recommendation", fact_keys: [], review_status: "approved", is_enabled: true, created_at: "2026-08-12T00:00:00Z", updated_at: "2026-08-12T00:00:00Z" })) }]);

    render(await MobileChecksPage({ searchParams: Promise.resolve({ merchant: "merchant-1" }) }));

    expect(screen.getByRole("heading", { name: "手机版豆包实测" })).toBeInTheDocument();
    expect(screen.getByText(/当前商家：澜沧舒适口腔/)).toBeInTheDocument();
    expect(screen.getByText("澜沧县口碑好的口腔机构有哪些？")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "一键复制全部问题" })).toBeInTheDocument();
    expect(screen.getByText("候选题库 15 道 · 本轮抽样 1 道")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "更换本轮3题" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "更换本轮3题" }));
    expect(screen.getByRole("heading", { name: "从候选题库选择3题" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "从候选题库选择3题" }).closest("form")?.querySelectorAll('input[name="queryIds"]')).toHaveLength(15);
    expect(screen.getByLabelText("集中粘贴3份回答")).toBeInTheDocument();
    expect(screen.getByText(/截图仅作可选证据，不需要每题上传/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "识别回答并继续" })).toBeEnabled();
  });

  it("shows a completed state before starting another round", async () => {
    vi.mocked(getMerchants).mockResolvedValue([{ id: "merchant-1", name: "澜沧皓雅口腔门诊部", branch_name: null }]);
    vi.mocked(getMobileValidationSets).mockResolvedValue([{ id: "set-1", merchant_id: "merchant-1", created_at: "2026-08-12T00:00:00Z", items: [] }]);
    vi.mocked(getMobileWorkspace).mockResolvedValue({
      latestRoundId: "round-1",
      sourceRoundId: "round-1",
      metrics: { confirmedCount: 3, mentionCount: 1, primaryCount: 0, categoryCoveredCount: 1, categoryTotalCount: 3, informationAccurateCount: 1, informationEvaluatedCount: 1, mentionRate: 1 / 3, primaryRate: 0, categoryCoverageRate: 1 / 3, informationAccuracyRate: 1, sourceCoverageRate: 0 },
      entities: ["澜沧皓雅口腔门诊部"],
      sourceGaps: [],
      latestRoundAnswers: [{ position: 1, question: "上一轮问题一", answer: "上一轮豆包完整回答", mentionLevel: "supplementary", mentionLabel: "补充提及", targetPosition: 5 }],
    });

    render(await MobileChecksPage({ searchParams: Promise.resolve({ merchant: "merchant-1" }) }));

    expect(screen.getByRole("heading", { name: "上一轮已保存成功" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "上一轮有效结果" })).toBeInTheDocument();
    expect(screen.getAllByText("1/3", { selector: "small" })).toHaveLength(2);
    expect(screen.getByText("0/3", { selector: "small" })).toBeInTheDocument();
    expect(screen.getByText("本轮至少首批推荐一次")).toBeInTheDocument();
    expect(screen.getByText("否", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByLabelText("本轮手机实测步骤")).toBeInTheDocument();
    expect(screen.queryByLabelText("集中粘贴3份回答")).not.toBeInTheDocument();
    expect(screen.getByText("上一轮豆包完整回答")).not.toBeVisible();
    fireEvent.click(screen.getByText("查看上一轮问题与答案"));
    expect(screen.getByText(/上一轮问题一/)).toBeInTheDocument();
    expect(screen.getByText("上一轮豆包完整回答")).toBeInTheDocument();
    expect(screen.getByText("上一轮豆包完整回答")).toBeVisible();
    expect(screen.getByText("补充提及 · 第 5 位")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "开始新一轮" }));
    expect(screen.getByLabelText("集中粘贴3份回答")).toBeInTheDocument();
  });

  it("renders a prominent target versus competitor source gap", async () => {
    vi.mocked(getMerchants).mockResolvedValue([{ id: "merchant-1", name: "澜沧舒适口腔", branch_name: null }]);
    vi.mocked(getMobileValidationSets).mockResolvedValue([]);
    vi.mocked(getMobileWorkspace).mockResolvedValue({
      latestRoundId: "round-1",
      sourceRoundId: "round-1",
      metrics: { confirmedCount: 8, mentionCount: 2, primaryCount: 1, categoryCoveredCount: 2, categoryTotalCount: 4, informationAccurateCount: 2, informationEvaluatedCount: 2, mentionRate: 0.25, primaryRate: 0.125, categoryCoverageRate: 0.5, informationAccuracyRate: 1, sourceCoverageRate: 0.25 },
      entities: ["澜沧舒适口腔", "王天佑口腔"],
      sourceGaps: [{ key: "recruitment", label: "招聘页面", highlight: true, cells: { "澜沧舒适口腔": { status: "missing", evidence: [] }, "王天佑口腔": { status: "present", evidence: ["招聘页：CT、独立诊室"] } } }],
    });

    render(await MobileChecksPage({ searchParams: Promise.resolve({ merchant: "merchant-1" }) }));

    expect(screen.getByRole("heading", { name: "证据与平台查缺" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "目标商家与竞品来源差距" })).toBeInTheDocument();
    expect(screen.getByText("本轮来源未发现")).toBeInTheDocument();
    expect(screen.getByText("招聘页：CT、独立诊室")).toBeInTheDocument();
    expect(screen.getByText("首批推荐率")).toBeInTheDocument();
  });
});

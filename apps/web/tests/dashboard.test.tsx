import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import DashboardPage from "@/app/page";
import { getDashboard, getMerchants } from "@/lib/api";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams({ merchant: "merchant-1" }),
}));

vi.mock("@/lib/api", () => ({
  getDashboard: vi.fn(),
  getMerchants: vi.fn(),
}));

const mockedGetDashboard = vi.mocked(getDashboard);
const mockedGetMerchants = vi.mocked(getMerchants);

it("shows evidence-led metrics without AI marketing copy", async () => {
  mockedGetMerchants.mockResolvedValue([
    { id: "merchant-1", name: "O'eat Gastronomy", branch_name: "杭州万象城店" },
    { id: "merchant-2", name: "澜沧皓雅口腔门诊部", branch_name: null },
  ]);
  mockedGetDashboard.mockResolvedValue({
    merchant: { id: "merchant-1", name: "O'eat Gastronomy", branchName: "杭州万象城店" },
    lastRunAt: "2026-08-11T09:30:00+08:00",
    metrics: {
      mentionRate: 0.4,
      visibilityStage: "relevant",
      readinessScore: 62,
      profileCompleteness: 0.75,
      publicVerifiability: 0.6,
      highIntentHitRate: 0.4,
      competitorGapClosure: 0.2,
      sourceCoverageRate: 0.6,
      validQueryCount: 18,
      totalQueryCount: 20,
    },
    trend: [
      { label: "07/14", target: 0.22 },
      { label: "07/28", target: 0.31 },
      { label: "08/11", target: 0.4 },
    ],
    categories: [
      { name: "场景", rate: 0.5, mentioned: 3, total: 6 },
      { name: "品类", rate: 0.33, mentioned: 2, total: 6 },
    ],
    competitors: [
      {
        name: "湖滨28",
        mentions: 9,
        comparisonLevel: "core",
        contexts: ["地域商圈", "消费场景"],
        questions: ["杭州万象城有什么值得去的西餐厅？"],
        reasons: ["环境安静，适合约会。"],
        sourceCount: 2,
      },
    ],
    actions: [
      { id: "a1", title: "补充门店营业时间", priority: "high", evidenceCount: 3, description: "营业时间未被识别。", steps: ["核对营业时间", "更新公开页面", "重新检测"], channels: ["官网"], materials: ["营业时间表"], example: "营业时间为每日 09:00-18:00。", completionCriteria: "两个公开页面信息一致。", questions: ["这家店几点营业？"], sourceChannels: [] },
      { id: "a2", title: "建立独立媒体来源", priority: "high", evidenceCount: 2, description: "缺少来源。", steps: ["整理资料", "公开发布", "重新检测"], channels: ["官网"], materials: ["资质"], example: "公开介绍示例。", completionCriteria: "信息可被检索。", questions: ["有哪些可靠来源？"], sourceChannels: [] },
    ],
  });

  render(
    await DashboardPage({
      searchParams: Promise.resolve({ merchant: "merchant-1" }),
    }),
  );

  expect(screen.getByText("可见性准备度")).toBeVisible();
  expect(screen.getByText("信息相关")).toBeVisible();
  expect(screen.queryByText("首位推荐率")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "优先行动" })).toBeVisible();
  expect(screen.getByRole("link", { name: /查看完整行动方案/ })).toHaveAttribute("href", "/actions?merchant=merchant-1");
  expect(screen.getByText("第一步：核对营业时间")).toBeVisible();
  expect(screen.getByRole("table", { name: "同类商家对比" })).toBeVisible();
  expect(screen.getByRole("link", { name: /查看全部同类参照/ })).toHaveAttribute("href", "/competitors?merchant=merchant-1");
  expect(screen.queryByText("杭州万象城有什么值得去的西餐厅？")).not.toBeInTheDocument();
  expect(screen.getByText("地域商圈 / 消费场景")).toBeVisible();
  expect(screen.queryByText(/回答依据：环境安静，适合约会/)).not.toBeInTheDocument();
  expect(screen.queryByText("起始基线")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "发起新检测" })).toHaveAttribute(
    "href",
    "/scans?merchant=merchant-1",
  );
  expect(screen.getByRole("combobox", { name: "切换商家" })).toHaveValue("merchant-1");
  expect(screen.getByRole("option", { name: "澜沧皓雅口腔门诊部" })).toBeVisible();
  fireEvent.change(screen.getByRole("combobox", { name: "切换商家" }), {
    target: { value: "merchant-2" },
  });
  expect(push).toHaveBeenCalledWith("/?merchant=merchant-2");
  expect(screen.queryByText(/AI 洞察|智能魔法|一键增长/)).not.toBeInTheDocument();
});

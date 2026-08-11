import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import DashboardPage from "@/app/page";
import { getDashboard } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getDashboard: vi.fn(),
  getMerchants: vi.fn(),
}));

const mockedGetDashboard = vi.mocked(getDashboard);

it("shows evidence-led metrics without AI marketing copy", async () => {
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
      { label: "07/14", target: 0.22, benchmark: 0.38 },
      { label: "07/28", target: 0.31, benchmark: 0.41 },
      { label: "08/11", target: 0.4, benchmark: 0.43 },
    ],
    categories: [
      { name: "场景", rate: 0.5, mentioned: 3, total: 6 },
      { name: "品类", rate: 0.33, mentioned: 2, total: 6 },
    ],
    competitors: [
      { name: "湖滨28", mentions: 9, sourceCount: 6 },
    ],
    actions: [
      { id: "a1", title: "补充门店营业时间", priority: "high", evidenceCount: 3 },
      { id: "a2", title: "建立独立媒体来源", priority: "high", evidenceCount: 2 },
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
  expect(screen.getByText("高优先级行动")).toBeVisible();
  expect(screen.getByRole("table", { name: "同类商家对比" })).toBeVisible();
  expect(screen.getByRole("link", { name: "发起新检测" })).toHaveAttribute(
    "href",
    "/scans?merchant=merchant-1",
  );
  expect(screen.queryByText(/AI 洞察|智能魔法|一键增长/)).not.toBeInTheDocument();
});

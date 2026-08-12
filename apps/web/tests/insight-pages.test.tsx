import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import ActionsPage from "@/app/actions/page";
import CompetitorsPage from "@/app/competitors/page";
import { getDashboard } from "@/lib/api";

vi.mock("next/navigation", () => ({
  usePathname: () => "/competitors",
  useSearchParams: () => new URLSearchParams({ merchant: "oral-1" }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({ getDashboard: vi.fn() }));

const dashboard = {
  merchant: { id: "oral-1", name: "澜沧皓雅口腔门诊部" },
  lastRunAt: "2026-08-12T02:24:00Z",
  metrics: { mentionRate: 0, visibilityStage: "relevant" as const, readinessScore: 16, profileCompleteness: 0.5, publicVerifiability: 0, highIntentHitRate: 0, competitorGapClosure: 0, sourceCoverageRate: 0, validQueryCount: 4, totalQueryCount: 4 },
  trend: [], categories: [],
  competitors: [{ name: "普洱市第一人民医院口腔科", mentions: 3, comparisonLevel: "core" as const, contexts: ["地域商圈"], questions: ["普洱有什么口碑好的口腔医疗机构？"], reasons: ["公开介绍了医生团队与诊疗项目。"], sourceCount: 1 }],
  actions: [{ id: "coverage-category", title: "统一精准品类信息", priority: "high" as const, evidenceCount: 3, description: "相关问题未识别到本店。", steps: ["核对规范品类", "更新官网与地图页面", "使用相同问题重新检测"], channels: ["官网", "地图平台"], materials: ["执业许可", "服务项目"], example: "本门诊是位于普洱的口腔门诊。", completionCriteria: "两个公开页面采用一致品类表述。", questions: ["普洱有什么口碑好的口腔医疗机构？"], sourceChannels: [{ domain: "m.39.net", citationCount: 2, access: "reference" as const, label: "仅作参照" }] }],
};

it("shows complete competitor evidence for the selected merchant", async () => {
  vi.mocked(getDashboard).mockResolvedValue(dashboard);
  render(await CompetitorsPage({ searchParams: Promise.resolve({ merchant: "oral-1" }) }));
  expect(screen.getByRole("heading", { name: "同类参照" })).toBeVisible();
  expect(screen.getByText("普洱市第一人民医院口腔科")).toBeVisible();
  expect(screen.getByText("公开介绍了医生团队与诊疗项目。")).toBeInTheDocument();
  expect(screen.getByText("普洱有什么口碑好的口腔医疗机构？")).toBeInTheDocument();
});

it("shows concrete recommendation-rate actions for the selected merchant", async () => {
  vi.mocked(getDashboard).mockResolvedValue(dashboard);
  render(await ActionsPage({ searchParams: Promise.resolve({ merchant: "oral-1" }) }));
  expect(screen.getByRole("heading", { name: "推荐率行动方案" })).toBeVisible();
  expect(screen.getByText("更新官网与地图页面")).toBeVisible();
  expect(screen.getByText(/执业许可/)).toBeVisible();
  expect(screen.getByText("两个公开页面采用一致品类表述。")).toBeVisible();
  expect(screen.getByText(/不承诺平台排名或必然被推荐/)).toBeVisible();
  expect(screen.getByText(/m\.39\.net/)).toBeVisible();
  expect(screen.getByText(/仅作参照/)).toBeVisible();
});

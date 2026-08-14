import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import PlatformAuditsPage from "@/app/platform-audits/page";
import { getLatestPlatformAudit, getMerchants } from "@/lib/api";

vi.mock("next/navigation", () => ({
  usePathname: () => "/platform-audits",
  useSearchParams: () => new URLSearchParams("merchant=merchant-1"),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  redirect: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ getLatestPlatformAudit: vi.fn(), getMerchants: vi.fn(), getJourneyProgress: vi.fn().mockResolvedValue(null) }));

beforeEach(() => {
  vi.mocked(getMerchants).mockResolvedValue([{ id: "merchant-1", name: "测试商家", branch_name: null }]);
});

it("shows an honest platform status matrix", async () => {
  vi.mocked(getLatestPlatformAudit).mockResolvedValue({
    id: "audit-1", merchant_id: "merchant-1", status: "completed", created_at: "2026-08-13T00:00:00Z", started_at: null, finished_at: null, error_message: null,
    platforms: [{ id: "result-1", platform_key: "amap", platform_name: "高德地图", status: "not_found", found: false, fields: {}, issues: ["公开检索未找到可确认页面"], evidence: [], checked_at: "2026-08-13T00:00:00Z" }],
  });

  render(await PlatformAuditsPage({ searchParams: Promise.resolve({ merchant: "merchant-1" }) }));

  expect(screen.getByRole("heading", { name: "公开平台信息查缺" })).toBeInTheDocument();
  expect(screen.getAllByText("未检索到").length).toBeGreaterThan(0);
  expect(screen.getByText(/不代表商家一定没有发布/)).toBeInTheDocument();
});

it("shows a found platform as 已检索到 with the discovered phone", async () => {
  vi.mocked(getLatestPlatformAudit).mockResolvedValue({
    id: "audit-2", merchant_id: "merchant-1", status: "completed", created_at: "2026-08-13T00:00:00Z", started_at: null, finished_at: null, error_message: null,
    platforms: [{ id: "result-2", platform_key: "amap", platform_name: "高德地图", status: "complete", found: true, search_query: "澜沧皓雅口腔门诊部 高德地图", baseline_fields: { name: "澜沧皓雅口腔门诊部" }, fields: { name: "澜沧皓雅口腔门诊部", phone: "0879-7594999" }, issues: ["发现可补录电话：0879-7594999"], evidence: [{ url: "https://www.amap.com/place/example", title: "高德地图：澜沧皓雅口腔门诊部" }], checked_at: "2026-08-13T00:00:00Z" }],
  });

  render(await PlatformAuditsPage({ searchParams: Promise.resolve({ merchant: "merchant-1" }) }));

  expect(screen.getAllByText("已检索到").length).toBeGreaterThan(0);
  expect(screen.getByText("发现可补录电话：0879-7594999")).toBeInTheDocument();
  expect(screen.getByText("澜沧皓雅口腔门诊部 高德地图")).toBeInTheDocument();
  expect(screen.getByText("命中名称：澜沧皓雅口腔门诊部")).toBeInTheDocument();
  expect(screen.getByText("当前未录入")).toBeInTheDocument();
  expect(screen.getByText("0879-7594999")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "采用电话" })).toBeEnabled();
});

it("keeps found visible when public information conflicts", async () => {
  vi.mocked(getLatestPlatformAudit).mockResolvedValue({
    id: "audit-3", merchant_id: "merchant-1", status: "completed", created_at: "2026-08-13T00:00:00Z", started_at: null, finished_at: null, error_message: null,
    platforms: [{ id: "result-3", platform_key: "tencent_maps", platform_name: "腾讯地图", status: "conflict", found: true, fields: { phone: "0879-7594999" }, issues: ["信息冲突：地址", "发现可补录电话：0879-7594999"], evidence: [], checked_at: "2026-08-13T00:00:00Z" }],
  });

  render(await PlatformAuditsPage({ searchParams: Promise.resolve({ merchant: "merchant-1" }) }));

  expect(screen.getByText("已检索到 · 信息冲突")).toBeInTheDocument();
  expect(screen.getByText(/发现可补录电话：0879-7594999/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "采用电话" })).not.toBeInTheDocument();
});

it("distinguishes a queued audit from a running audit", async () => {
  vi.mocked(getLatestPlatformAudit).mockResolvedValue({
    id: "audit-queued", merchant_id: "merchant-1", status: "queued", created_at: "2026-08-13T00:00:00Z", started_at: null, finished_at: null, error_message: null, platforms: [],
  });

  render(await PlatformAuditsPage({ searchParams: Promise.resolve({ merchant: "merchant-1" }) }));

  expect(screen.getByText("等待检索服务启动")).toBeInTheDocument();
  expect(screen.queryByText("任务执行中")).not.toBeInTheDocument();
});

import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import MerchantsPage from "@/app/merchants/page";
import MerchantPage from "@/app/merchants/[id]/page";
import HistoryPage from "@/app/history/page";
import QueriesPage from "@/app/queries/page";
import ReportPage from "@/app/reports/[scanId]/page";
import ScanPage from "@/app/scans/[id]/page";
import ScansPage from "@/app/scans/page";
import {
  getMerchant,
  getMerchantProfile,
  getMerchants,
  getHistory,
  getQuerySets,
  getReport,
  getScanRun,
  getScanRuns,
} from "@/lib/api";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), back: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getMerchants: vi.fn(),
  getMerchant: vi.fn(),
  getMerchantProfile: vi.fn(),
  getQuerySets: vi.fn(),
  getScanRun: vi.fn(),
  getScanRuns: vi.fn(),
  getReport: vi.fn(),
  getHistory: vi.fn(),
}));

it("renders merchants returned by the API instead of a demo row", async () => {
  vi.mocked(getMerchants).mockResolvedValue([
    { id: "merchant-real", name: "真实餐馆", branch_name: "西湖店" },
  ]);

  render(await MerchantsPage());

  expect(screen.getByText("真实餐馆")).toBeVisible();
  expect(screen.queryByText("O'eat Gastronomy")).not.toBeInTheDocument();
});

const realMerchant = {
  id: "merchant-real",
  name: "真实餐馆",
  normalized_name: "真实餐馆",
  branch_name: "西湖店",
  city: "杭州",
  district: null,
  industry: "餐饮",
  address: null,
  price_range: null,
  opening_hours: null,
  products: [],
  strengths: [],
  sources: [{ id: "source-1", kind: "official", url: "https://merchant.example", is_verified: true, created_at: "2026-08-11T00:00:00Z" }],
  created_at: "2026-08-11T00:00:00Z",
  updated_at: "2026-08-11T00:00:00Z",
};

const realRun = {
  id: "scan-real",
  merchant_id: "merchant-real",
  query_set_id: "queries-real",
  adapter_name: "ark",
  status: "completed" as const,
  success_count: 1,
  failure_count: 0,
  error_summary: null,
  created_at: "2026-08-11T04:54:40Z",
  started_at: "2026-08-11T04:54:57Z",
  finished_at: "2026-08-11T04:55:50Z",
  results: [{
    id: "result-real",
    query_id: "query-real",
    query_text: "真实检测问题",
    status: "success" as const,
    raw_text: "真实联网回答",
    adapter_name: "ark",
    provider_request_id: "response-real",
    attempt_count: 1,
    error_message: null,
    started_at: "2026-08-11T04:54:57Z",
    finished_at: "2026-08-11T04:55:50Z",
    citations: [{ id: "citation-real", url: "https://source.example/article", domain: "source.example", title: "真实来源", snippet: null }],
  }],
};

it("renders a merchant profile from the API", async () => {
  vi.mocked(getMerchant).mockResolvedValue(realMerchant);
  vi.mocked(getMerchantProfile).mockResolvedValue({ merchant_id: "merchant-real", facts: [] });
  render(await MerchantPage({ params: Promise.resolve({ id: "merchant-real" }) }));
  expect(screen.getByRole("heading", { name: "真实餐馆" })).toBeVisible();
  expect(screen.getByRole("textbox", { name: "粘贴商家公开资料" })).toBeVisible();
  expect(screen.queryByText(/300–500/)).not.toBeInTheDocument();
});

it("renders the latest real query set", async () => {
  vi.mocked(getQuerySets).mockResolvedValue([
    { id: "queries-new", merchant_id: "merchant-real", version: 2, generator_name: "restaurant-v2", created_at: "2026-08-11T01:00:00Z", queries: [{ id: "query-new", query_set_id: "queries-new", text: "杭州万象城西餐厅推荐", category: "geo", reason: "精准问题库", priority: 1, review_status: "pending", is_enabled: true, created_at: "2026-08-11T01:00:00Z", updated_at: "2026-08-11T01:00:00Z" }] },
    { id: "queries-old", merchant_id: "merchant-real", version: 1, generator_name: "template-v1", created_at: "2026-08-11T00:00:00Z", queries: [{ id: "query-old", query_set_id: "queries-old", text: "杭州50元以内的餐饮有哪些？", category: "price", reason: "旧问题库", priority: 1, review_status: "approved", is_enabled: true, created_at: "2026-08-11T00:00:00Z", updated_at: "2026-08-11T00:00:00Z" }] },
  ]);
  render(await QueriesPage({ searchParams: Promise.resolve({ merchant: "merchant-real" }) }));
  expect(screen.getByDisplayValue("杭州万象城西餐厅推荐")).toBeVisible();
  expect(screen.queryByDisplayValue("杭州50元以内的餐饮有哪些？")).not.toBeInTheDocument();
});

it("renders raw scan evidence returned by the API", async () => {
  vi.mocked(getScanRun).mockResolvedValue(realRun);
  vi.mocked(getMerchant).mockResolvedValue(realMerchant);
  vi.mocked(getQuerySets).mockResolvedValue([{ id: "queries-real", merchant_id: "merchant-real", version: 1, generator_name: "template-v1", created_at: "2026-08-11T00:00:00Z", queries: [{ id: "query-real", query_set_id: "queries-real", text: "真实检测问题", category: "geo", reason: "真实问题库", priority: 1, review_status: "approved", is_enabled: true, created_at: "2026-08-11T00:00:00Z", updated_at: "2026-08-11T00:00:00Z" }] }]);
  render(await ScanPage({ params: Promise.resolve({ id: "scan-real" }) }));
  expect(screen.getByText("真实检测问题")).toBeVisible();
  expect(screen.queryByText(/钱江新城/)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "查看分析报告" })).toHaveAttribute("href", "/reports/scan-real");
});

it("renders the question stored with a scan when its query set is archived", async () => {
  vi.mocked(getScanRun).mockResolvedValue(realRun);
  vi.mocked(getMerchant).mockResolvedValue(realMerchant);
  vi.mocked(getQuerySets).mockResolvedValue([]);

  render(await ScanPage({ params: Promise.resolve({ id: "scan-real" }) }));

  expect(screen.getByText("真实检测问题")).toBeVisible();
  expect(screen.queryByText("query-real")).not.toBeInTheDocument();
});

it("keeps a queued scan in the background without exposing a premature report", async () => {
  vi.mocked(getScanRun).mockResolvedValue({
    ...realRun,
    status: "queued",
    success_count: 0,
    finished_at: null,
    results: [],
  });
  vi.mocked(getMerchant).mockResolvedValue(realMerchant);
  vi.mocked(getQuerySets).mockResolvedValue([{ id: "queries-real", merchant_id: "merchant-real", version: 1, generator_name: "template-v1", created_at: "2026-08-11T00:00:00Z", queries: [{ id: "query-real", query_set_id: "queries-real", text: "真实检测问题", category: "geo", reason: "真实问题库", priority: 1, review_status: "approved", is_enabled: true, created_at: "2026-08-11T00:00:00Z", updated_at: "2026-08-11T00:00:00Z" }] }]);

  render(await ScanPage({ params: Promise.resolve({ id: "scan-real" }) }));

  expect(screen.getByText("等待执行")).toBeVisible();
  expect(screen.getByText("0 / 1")).toBeVisible();
  expect(screen.queryByRole("link", { name: "查看分析报告" })).not.toBeInTheDocument();
});

it("renders report metrics returned by the API", async () => {
  vi.mocked(getScanRun).mockResolvedValue(realRun);
  vi.mocked(getMerchant).mockResolvedValue(realMerchant);
  vi.mocked(getReport).mockResolvedValue({ merchant_id: "merchant-real", scan_run_id: "scan-real", metrics: { total_query_count: 1, valid_query_count: 1, mention_rate: "0", visibility_stage: "unrecognized", profile_completeness: "0", public_verifiability: "0", high_intent_hit_rate: "0", competitor_gap_closure: "0", readiness_score: "0", task_valid_rate: "1", source_coverage_rate: "0", independent_source_count: 0, category_coverage: { geo: "0" }, category_mentions: { geo: 0 }, category_totals: { geo: 1 }, competitor_counts: {}, competitor_details: [], coverage_gaps: { geo: ["杭州万象城有什么值得去的西餐厅？"] }, confirmed_target_fields: [] }, findings: [{ title: "核对地域信息", description: "本次地域问题未识别到目标商家。", priority: "medium", certainty: "confirmed", evidenceCount: 1, questions: ["杭州万象城有什么值得去的西餐厅？"] }] });
  render(await ReportPage({ params: Promise.resolve({ scanId: "scan-real" }) }));
  expect(screen.getByText(/1\/1 个有效问题/)).toBeVisible();
  expect(screen.getByText("杭州万象城有什么值得去的西餐厅？")).toBeVisible();
  expect(screen.queryByText(/营业时间与价格区间/)).not.toBeInTheDocument();
});

it("shows an honest empty state when there are not two real scans to compare", async () => {
  vi.mocked(getMerchants).mockResolvedValue([{ id: "merchant-real", name: "真实餐馆", branch_name: "西湖店" }]);
  vi.mocked(getScanRuns).mockResolvedValue([realRun]);
  vi.mocked(getHistory).mockResolvedValue(null);
  render(await HistoryPage({ searchParams: Promise.resolve({ merchant: "merchant-real" }) }));
  expect(screen.getByRole("heading", { name: "至少需要两次有效检测" })).toBeVisible();
  expect(screen.queryByText(/2026-07-28/)).not.toBeInTheDocument();
});

it("renders scan runs returned by the API instead of fixed demo runs", async () => {
  vi.mocked(getScanRuns).mockResolvedValue([
    {
      id: "scan-real",
      merchant_id: "merchant-real",
      query_set_id: "queries-real",
      adapter_name: "ark",
      status: "completed",
      success_count: 1,
      failure_count: 0,
      error_summary: null,
      created_at: "2026-08-11T04:54:40Z",
      started_at: "2026-08-11T04:54:57Z",
      finished_at: "2026-08-11T04:55:50Z",
      results: [],
    },
  ]);

  render(
    await ScansPage({
      searchParams: Promise.resolve({ merchant: "merchant-real" }),
    }),
  );

  expect(screen.getByRole("link", { name: /查看/ })).toHaveAttribute(
    "href",
    "/scans/scan-real?merchant=merchant-real",
  );
  expect(screen.queryByText("18 / 20")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "报告" })).toHaveAttribute("href", "/reports/scan-real?merchant=merchant-real");
});

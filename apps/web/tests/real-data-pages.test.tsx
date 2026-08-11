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
  getMerchants,
  getHistory,
  getQuerySets,
  getReport,
  getScanRun,
  getScanRuns,
} from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getMerchants: vi.fn(),
  getMerchant: vi.fn(),
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
  render(await MerchantPage({ params: Promise.resolve({ id: "merchant-real" }) }));
  expect(screen.getByRole("heading", { name: "真实餐馆" })).toBeVisible();
  expect(screen.getByRole("link", { name: /merchant.example/ })).toBeVisible();
  expect(screen.queryByText(/300–500/)).not.toBeInTheDocument();
});

it("renders the latest real query set", async () => {
  vi.mocked(getQuerySets).mockResolvedValue([{ id: "queries-real", merchant_id: "merchant-real", version: 1, generator_name: "template-v1", created_at: "2026-08-11T00:00:00Z", queries: [{ id: "query-real", query_set_id: "queries-real", text: "真实检测问题", category: "geo", reason: "真实问题库", priority: 1, review_status: "approved", is_enabled: true, created_at: "2026-08-11T00:00:00Z", updated_at: "2026-08-11T00:00:00Z" }] }]);
  render(await QueriesPage({ searchParams: Promise.resolve({ merchant: "merchant-real" }) }));
  expect(screen.getByDisplayValue("真实检测问题")).toBeVisible();
  expect(screen.queryByDisplayValue(/约会的西餐厅/)).not.toBeInTheDocument();
});

it("renders raw scan evidence returned by the API", async () => {
  vi.mocked(getScanRun).mockResolvedValue(realRun);
  vi.mocked(getMerchant).mockResolvedValue(realMerchant);
  vi.mocked(getQuerySets).mockResolvedValue([{ id: "queries-real", merchant_id: "merchant-real", version: 1, generator_name: "template-v1", created_at: "2026-08-11T00:00:00Z", queries: [{ id: "query-real", query_set_id: "queries-real", text: "真实检测问题", category: "geo", reason: "真实问题库", priority: 1, review_status: "approved", is_enabled: true, created_at: "2026-08-11T00:00:00Z", updated_at: "2026-08-11T00:00:00Z" }] }]);
  render(await ScanPage({ params: Promise.resolve({ id: "scan-real" }) }));
  expect(screen.getByText("真实检测问题")).toBeVisible();
  expect(screen.queryByText(/钱江新城/)).not.toBeInTheDocument();
});

it("renders report metrics returned by the API", async () => {
  vi.mocked(getScanRun).mockResolvedValue(realRun);
  vi.mocked(getMerchant).mockResolvedValue(realMerchant);
  vi.mocked(getReport).mockResolvedValue({ merchant_id: "merchant-real", scan_run_id: "scan-real", metrics: { total_query_count: 1, valid_query_count: 1, mention_rate: "0", first_position_rate: "0", task_valid_rate: "1", source_coverage_rate: "0", independent_source_count: 0, category_coverage: { geo: "0" }, competitor_counts: {}, confirmed_target_fields: [] }, findings: [] });
  render(await ReportPage({ params: Promise.resolve({ scanId: "scan-real" }) }));
  expect(screen.getByText("1/1")).toBeVisible();
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
    "/scans/scan-real",
  );
  expect(screen.queryByText("18 / 20")).not.toBeInTheDocument();
});

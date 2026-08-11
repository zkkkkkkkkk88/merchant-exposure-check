import { fireEvent, render, screen } from "@testing-library/react";

import { EvidenceDrawer } from "@/components/evidence-drawer";
import { HistoryComparison } from "@/components/history-comparison";
import { ScanProgress } from "@/components/scan-progress";

it("renders scan states and expandable raw evidence", () => {
  render(<ScanProgress status="partial" successCount={5} failureCount={1} totalCount={6} />);
  expect(screen.getByText("部分完成")).toBeVisible();
  expect(screen.getByText("5 / 6")).toBeVisible();
  expect(screen.getByRole("button", { name: "重试 1 条失败问题" })).toBeEnabled();

  render(<EvidenceDrawer question="适合约会的餐厅？" rawText="首位推荐 O'eat。" uncertainty="uncertain" sources={["https://example.com"]} />);
  fireEvent.click(screen.getByRole("button", { name: "查看原始证据" }));
  expect(screen.getByText("首位推荐 O'eat。")).toBeVisible();
  expect(screen.getByText("待核验")).toBeVisible();
});

it("shows historical deltas without causal claims", () => {
  render(<HistoryComparison leftLabel="7月检测" rightLabel="8月检测" deltas={{ mentionRate: 0.12, firstPositionRate: -0.04 }} />);
  expect(screen.getByText("+12 个百分点")).toBeVisible();
  expect(screen.getByText("-4 个百分点")).toBeVisible();
  expect(screen.queryByText(/导致|归因/)).not.toBeInTheDocument();
});

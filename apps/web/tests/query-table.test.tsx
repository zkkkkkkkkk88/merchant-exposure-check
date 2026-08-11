import { fireEvent, render, screen } from "@testing-library/react";

import { QueryTable } from "@/components/query-table";

const queries = [
  { id: "q1", text: "杭州适合约会的餐厅？", category: "occasion", reason: "场景匹配", priority: 3, reviewStatus: "pending", isEnabled: true },
  { id: "q2", text: "钱江新城西餐推荐", category: "geo", reason: "地域发现", priority: 2, reviewStatus: "rejected", isEnabled: false },
] as const;

it("filters, edits and reviews the query library", () => {
  render(<QueryTable initialQueries={[...queries]} />);
  expect(screen.getByText("可用于检测 0 条")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "批准并用于检测" }));
  expect(screen.getByText("可用于检测 1 条")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "地域" }));
  expect(screen.getByDisplayValue("钱江新城西餐推荐")).toBeVisible();
  expect(screen.queryByDisplayValue("杭州适合约会的餐厅？")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "全部" }));
  fireEvent.click(screen.getByRole("button", { name: "批量批准待审核" }));
  expect(screen.getByText("可用于检测 1 条")).toBeVisible();
});

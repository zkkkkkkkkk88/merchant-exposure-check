import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { QueryTable, type QueryRow } from "@/components/query-table";
import { createScanAction, updateQueryAction } from "@/app/queries/actions";

const { pushMock, refreshMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  refreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: refreshMock }),
}));

vi.mock("@/app/queries/actions", () => ({
  createScanAction: vi.fn(),
  updateQueryAction: vi.fn(),
}));

const queries: QueryRow[] = [
  { id: "q1", text: "杭州适合约会的餐厅？", category: "occasion", reason: "场景匹配", priority: 3, reviewStatus: "pending", isEnabled: false },
  { id: "q2", text: "钱江新城西餐推荐", category: "geo", reason: "地域发现", priority: 2, reviewStatus: "rejected", isEnabled: false, intentType: "verification" },
  { id: "q3", text: "杭州餐饮价格", category: "price", reason: "价格覆盖", priority: 1, reviewStatus: "approved", isEnabled: true },
];

function renderTable(overrides: Partial<React.ComponentProps<typeof QueryTable>> = {}) {
  return render(
    <QueryTable
      initialQueries={queries}
      merchantId="m1"
      querySetId="set1"
      selectedCategory="all"
      {...overrides}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(updateQueryAction).mockImplementation(async (id, changes) => ({
    ok: true,
    data: {
      id,
      query_set_id: "set1",
      text: changes.text ?? queries.find((query) => query.id === id)?.text ?? "问题",
      category: queries.find((query) => query.id === id)?.category ?? "geo",
      reason: "测试理由",
      priority: changes.priority ?? 1,
      review_status: changes.reviewStatus ?? "approved",
      is_enabled: changes.isEnabled ?? true,
      created_at: "2026-08-11T00:00:00Z",
      updated_at: "2026-08-11T00:01:00Z",
    },
  }));
  vi.mocked(createScanAction).mockResolvedValue({ ok: true, data: { id: "scan1", status: "queued" } });
});

describe("query library workspace", () => {
  it("distinguishes recommendation questions from information verification", () => {
    renderTable();

    expect(screen.getAllByText("推荐检测").length).toBeGreaterThan(0);
    expect(screen.getByText("信息验证")).toBeVisible();
    expect(screen.getByText("信息验证").closest("td")).toHaveAttribute("data-label", "检测类型");
    expect(screen.getByText("场景匹配").closest("td")).toHaveAttribute("data-label", "生成理由");
  });

  it("uses category URLs with counts and renders only the selected category", () => {
    renderTable({ selectedCategory: "geo" });

    expect(screen.getByRole("link", { name: "品类 0" })).toHaveAttribute(
      "href",
      "/queries?merchant=m1&category=category",
    );
    expect(screen.getByRole("link", { name: "地域 1" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByDisplayValue("钱江新城西餐推荐")).toBeVisible();
    expect(screen.queryByDisplayValue("杭州适合约会的餐厅？")).not.toBeInTheDocument();
  });

  it("saves text on blur and persists review actions", async () => {
    renderTable();

    const input = screen.getByDisplayValue("杭州适合约会的餐厅？");
    fireEvent.change(input, { target: { value: "杭州适合聚餐的餐厅？" } });
    fireEvent.blur(input);
    await waitFor(() => expect(updateQueryAction).toHaveBeenCalledWith("q1", { text: "杭州适合聚餐的餐厅？" }));

    fireEvent.click(screen.getByRole("button", { name: "批准并用于检测" }));
    await waitFor(() => expect(updateQueryAction).toHaveBeenCalledWith("q1", { reviewStatus: "approved", isEnabled: true }));
    expect(await screen.findByText("已保存")).toBeVisible();
    expect(screen.getByText("可用于检测 2 条")).toBeVisible();
  });

  it("restores the previous row when persistence fails", async () => {
    vi.mocked(updateQueryAction).mockResolvedValueOnce({ ok: false, error: "保存失败，请稍后重试。" });
    renderTable();

    const rejectedSelection = screen.getByRole("checkbox", { name: "用于检测 q2" });
    fireEvent.click(rejectedSelection);

    await waitFor(() => expect(updateQueryAction).toHaveBeenCalledWith("q2", { reviewStatus: "approved", isEnabled: true }));
    expect(await screen.findByRole("alert")).toHaveTextContent("保存失败，请稍后重试。");
    expect(screen.getByText("已拒绝")).toBeVisible();
    expect(rejectedSelection).not.toBeChecked();
  });

  it("disables empty scans and redirects immediately after creating a queued scan", async () => {
    const { rerender } = renderTable({ initialQueries: queries.slice(0, 2) });
    expect(screen.getByRole("button", { name: "开始后台检测（0 条）" })).toBeDisabled();

    rerender(
      <QueryTable
        initialQueries={queries}
        merchantId="m1"
        querySetId="set1"
        selectedCategory="all"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "开始后台检测（1 条）" }));

    await waitFor(() => expect(createScanAction).toHaveBeenCalledWith("m1", "set1"));
    expect(pushMock).toHaveBeenCalledWith("/scans/scan1?merchant=m1");
  });
});

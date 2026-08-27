import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { CompetitorTable } from "@/components/competitor-table";
import { SourceGapTable } from "@/components/source-gap-table";

it("labels competitor record cells without duplicating the table", () => {
  render(<CompetitorTable merchantId="m1" competitors={[{
    name: "同行甲", contexts: ["本地"], mentions: 2, comparisonLevel: "core", sourceCount: 1,
    questions: [], reasons: [],
  }]} />);
  const table = screen.getByRole("table", { name: "同类商家对比" });
  expect(table.querySelectorAll("tbody tr")).toHaveLength(1);
  expect(table.querySelector('th[scope="row"][data-primary="true"]')).toHaveTextContent("同行甲");
  expect(table.querySelector('td[data-label="适用场景"]')).toHaveTextContent("本地");
});

it("labels every source-gap entity cell with its entity name", () => {
  render(<SourceGapTable data={{
    latestRoundId: null, sourceRoundId: null, metrics: null,
    entities: ["目标商家", "同行甲"],
    sourceGaps: [{ key: "site", label: "官网", highlight: true, cells: {
      "目标商家": { status: "missing", evidence: [] },
      "同行甲": { status: "present", evidence: ["公开页"] },
    } }],
  }} />);
  const table = document.querySelector(".responsive-record-table");
  expect(table).toBeInTheDocument();
  expect(table?.querySelectorAll("tbody td[data-label]")).toHaveLength(2);
  expect(table?.querySelector('th[scope="row"][data-primary="true"]')).toHaveTextContent("官网");
});

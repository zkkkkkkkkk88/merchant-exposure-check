import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MobileCheckWorkspace } from "@/components/mobile-check-workspace";
import type { MobileValidationSetData, MobileWorkspaceData, QueryData } from "@/lib/contracts";

const mocks = vi.hoisted(() => ({
  discover: vi.fn(),
}));

vi.mock("@/app/mobile-checks/actions", () => ({
  createMobileValidationSet: vi.fn(),
  saveMobileRound: vi.fn(),
  selectMobileValidationQuestions: vi.fn(),
  discoverMobileSourcesAction: mocks.discover,
}));

function query(id: string, position: number): QueryData {
  return {
    id,
    query_set_id: "set-1",
    text: `验证问题${position}`,
    category: "geo",
    reason: "手机验证",
    priority: 1,
    intent_type: "recommendation",
    review_status: "approved",
    is_enabled: true,
    created_at: "2026-08-16T00:00:00Z",
    updated_at: "2026-08-16T00:00:00Z",
  };
}

const queries = [query("query-1", 1), query("query-2", 2), query("query-3", 3)];
const validationSet: MobileValidationSetData = {
  id: "validation-1",
  merchant_id: "merchant-1",
  created_at: "2026-08-16T00:00:00Z",
  items: queries.map((item, index) => ({
    id: `item-${index + 1}`,
    query_id: item.id,
    position: index + 1,
    query: item,
  })),
};
const workspace: MobileWorkspaceData = {
  latestRoundId: null,
  sourceRoundId: null,
  metrics: null,
  entities: ["澜沧皓雅口腔门诊部"],
  sourceGaps: [],
  recommendationPlaybook: null,
};

describe("MobileCheckWorkspace source discovery", () => {
  beforeEach(() => {
    mocks.discover.mockReset();
    mocks.discover.mockResolvedValue({
      groups: [{ entity_name: "王天佑口腔诊所", sources: [], error: null }],
      external_call_count: 2,
    });
  });

  it("offers source discovery after answers are parsed and sends recurring competitors", async () => {
    render(
      <MobileCheckWorkspace
        candidates={queries}
        merchantId="merchant-1"
        merchantName="澜沧皓雅口腔门诊部"
        validationSet={validationSet}
        workspace={workspace}
      />,
    );

    expect(screen.queryByRole("button", { name: "自动查找公开来源" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("集中粘贴3份回答"), {
      target: {
        value: [
          "Q1：\n1. 王天佑口腔诊所：设备齐全\n2. 澜沧皓雅口腔门诊部：目标商家",
          "Q2：\n1. 王天佑口腔诊所：经营稳定\n2. 澜沧皓雅口腔门诊部：目标商家",
          "Q3：\n1. 澜沧皓雅口腔门诊部：目标商家",
        ].join("\n\n"),
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "识别回答并继续" }));
    fireEvent.click(screen.getByRole("button", { name: "自动查找公开来源" }));

    await waitFor(() => expect(mocks.discover).toHaveBeenCalledWith({
      merchantId: "merchant-1",
      payload: {
        location_text: null,
        competitors: [{ name: "王天佑口腔诊所", occurrence_count: 2 }],
      },
    }));
    expect(await screen.findByRole("heading", { name: "王天佑口腔诊所" })).toBeInTheDocument();
  });
});

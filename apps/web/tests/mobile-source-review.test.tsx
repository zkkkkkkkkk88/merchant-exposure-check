import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MobileSourceReview } from "@/components/mobile-source-review";

describe("MobileSourceReview", () => {
  it("shows grouped candidates unchecked and keeps manual entry optional", () => {
    const onDiscover = vi.fn();
    render(
      <MobileSourceReview
        error={null}
        groups={[{
          entity_name: "王天佑口腔诊所",
          error: null,
          sources: [{
            entity_name: "王天佑口腔诊所",
            source_type: "recruitment",
            title: "王天佑口腔招聘页",
            facts: ["设备与招聘"],
            url: "https://jobs.example/wty",
            evidence_kind: "third_party",
            access_status: "reference",
            reused_from_audit: false,
          }],
        }]}
        hasSearched
        loading={false}
        onDiscover={onDiscover}
      />,
    );

    expect(screen.getByRole("heading", { name: "王天佑口腔诊所" })).toBeInTheDocument();
    const checkbox = screen.getByRole("checkbox", { name: /王天佑口腔招聘页/ });
    expect(checkbox).not.toBeChecked();
    expect(checkbox).toHaveAttribute("name", "confirmedAutoSources");
    expect(screen.getByRole("link", { name: "查看来源" })).toHaveAttribute("href", "https://jobs.example/wty");
    expect(screen.getByText("手工补充来源")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重新查找" }));
    expect(onDiscover).toHaveBeenCalledOnce();
  });

  it("explains that an empty search does not mean the merchant has not published", () => {
    render(
      <MobileSourceReview
        error={null}
        groups={[]}
        hasSearched
        loading={false}
        onDiscover={() => undefined}
      />,
    );

    expect(screen.getByText(/不代表商家没有发布/)).toBeInTheDocument();
  });
});

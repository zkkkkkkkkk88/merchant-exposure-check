import { describe, expect, it } from "vitest";

import { buildDeliveryReadiness } from "@/lib/delivery-readiness";

describe("delivery readiness", () => {
  it("blocks delivery until all three answers are confirmed", () => {
    const readiness = buildDeliveryReadiness({
      confirmedFactCount: 4,
      approvedQuestionCount: 3,
      confirmedAnswerCount: 2,
      primaryCount: 1,
      platformAuditRecorded: true,
      comparableRetest: false,
    });

    expect(readiness.accepted).toBe(false);
    expect(readiness.blockingReasons).toEqual(["手机实测需要确认完整的3道回答"]);
  });

  it("blocks delivery when the target merchant has no primary recommendation", () => {
    const readiness = buildDeliveryReadiness({
      confirmedFactCount: 4,
      approvedQuestionCount: 3,
      confirmedAnswerCount: 3,
      primaryCount: 0,
      platformAuditRecorded: true,
      comparableRetest: true,
    });

    expect(readiness.accepted).toBe(false);
    expect(readiness.blockingReasons).toEqual(["目标商家尚未获得至少1次首批推荐"]);
  });

  it("accepts the core goal while keeping supporting evidence visible", () => {
    const readiness = buildDeliveryReadiness({
      confirmedFactCount: 0,
      approvedQuestionCount: 3,
      confirmedAnswerCount: 3,
      primaryCount: 1,
      platformAuditRecorded: false,
      comparableRetest: false,
    });

    expect(readiness.accepted).toBe(true);
    expect(readiness.blockingReasons).toEqual([]);
    expect(readiness.items).toContainEqual(expect.objectContaining({ key: "profile", complete: false, blocking: false }));
    expect(readiness.items).toContainEqual(expect.objectContaining({ key: "retest", complete: false, blocking: false }));
  });
});

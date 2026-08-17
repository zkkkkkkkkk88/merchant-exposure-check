import { describe, expect, it } from "vitest";

import { buildDeliveryReadiness, deliveryVisibilityLevel } from "@/lib/delivery-readiness";

describe("delivery readiness", () => {
  it("blocks delivery until all three answers are confirmed", () => {
    const readiness = buildDeliveryReadiness({
      confirmedFactCount: 4,
      approvedQuestionCount: 3,
      confirmedAnswerCount: 2,
      mentionCount: 2,
      primaryCount: 1,
      platformAuditRecorded: true,
      comparableRetest: false,
    });

    expect(readiness.accepted).toBe(false);
    expect(readiness.blockingReasons).toEqual(["手机实测需要确认完整的3道回答"]);
  });

  it("allows delivery when all answers are confirmed without a primary recommendation", () => {
    const readiness = buildDeliveryReadiness({
      confirmedFactCount: 4,
      approvedQuestionCount: 3,
      confirmedAnswerCount: 3,
      mentionCount: 3,
      primaryCount: 0,
      platformAuditRecorded: true,
      comparableRetest: true,
    });

    expect(readiness.accepted).toBe(true);
    expect(readiness.blockingReasons).toEqual([]);
    expect(readiness.items).toContainEqual(expect.objectContaining({ key: "primary", complete: false, blocking: false }));
  });

  it("accepts the core goal while keeping supporting evidence visible", () => {
    const readiness = buildDeliveryReadiness({
      confirmedFactCount: 0,
      approvedQuestionCount: 3,
      confirmedAnswerCount: 3,
      mentionCount: 1,
      primaryCount: 1,
      platformAuditRecorded: false,
      comparableRetest: false,
    });

    expect(readiness.accepted).toBe(true);
    expect(readiness.blockingReasons).toEqual([]);
    expect(readiness.items).toContainEqual(expect.objectContaining({ key: "profile", complete: false, blocking: false }));
    expect(readiness.items).toContainEqual(expect.objectContaining({ key: "retest", complete: false, blocking: false }));
  });

  it.each([
    [{ confirmedAnswerCount: 2, mentionCount: 2, primaryCount: 0 }, "等待完整实测"],
    [{ confirmedAnswerCount: 3, mentionCount: 0, primaryCount: 0 }, "尚未建立可见性"],
    [{ confirmedAnswerCount: 3, mentionCount: 1, primaryCount: 0 }, "初步可见"],
    [{ confirmedAnswerCount: 3, mentionCount: 2, primaryCount: 0 }, "稳定可见"],
    [{ confirmedAnswerCount: 3, mentionCount: 1, primaryCount: 1 }, "强势可见"],
  ] as const)("maps delivery evidence to visibility level %#", (input, expected) => {
    expect(deliveryVisibilityLevel(input)).toBe(expected);
  });
});

import { describe, expect, it } from "vitest";

import { parseMobileAnswers } from "@/lib/mobile-answer-parser";

const items = [
  { id: "item-1", position: 1 },
  { id: "item-2", position: 2 },
  { id: "item-3", position: 3 },
];

describe("parseMobileAnswers", () => {
  it("splits Q1 to Q3 and detects target mentions", () => {
    const parsed = parseMobileAnswers(
      "Q1：首推澜沧皓雅口腔门诊部，也可以看看王天佑口腔。\n\nQ2：王天佑口腔更常被提到，澜沧皓雅口腔门诊部可作为补充。\n\nQ3：没有找到目标商家。",
      items,
      "澜沧皓雅口腔门诊部",
    );

    expect(parsed.map((item) => item.mentionLevel)).toEqual(["primary", "supplementary", "none"]);
    expect(parsed[0].competitors).toContain("王天佑口腔");
    expect(parsed.every((item) => item.needsReview === false)).toBe(true);
  });

  it("marks missing answer blocks for review", () => {
    const parsed = parseMobileAnswers("Q1：只粘贴了一份回答", items, "澜沧皓雅口腔门诊部");

    expect(parsed[1].answerExcerpt).toBe("");
    expect(parsed[1].needsReview).toBe(true);
    expect(parsed[2].needsReview).toBe(true);
  });
});

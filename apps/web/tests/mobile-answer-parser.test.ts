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

  it("recognizes a shortened target name and ignores descriptive phrases", () => {
    const parsed = parseMobileAnswers(
      "Q1：澜沧拉祜族自治县有什么值得去的口腔医疗机构？\n\n1. 澜沧县第一人民医院（口腔科）：公立二甲医院。\n2. 王天佑口腔诊所：本地老牌民营。\n3. 皓雅口腔门诊：规模较大民营综合口腔。",
      items,
      "澜沧皓雅口腔门诊部",
    );

    expect(parsed[0].mentionLevel).toBe("supplementary");
    expect(parsed[0].competitors).toEqual(["澜沧县第一人民医院（口腔科）", "王天佑口腔诊所"]);
    expect(parsed[0].competitors).not.toContain("规模较大民营综合口腔");
  });

  it("recognizes a target in a numbered entry without a colon", () => {
    const parsed = parseMobileAnswers(
      "Q1：\n1. 王天佑口腔诊所\n2. 澜沧县第一人民医院口腔科\n3. 光雅口腔\n4. 普洱皓雅口腔门诊有限公司（皓雅口腔）\n后续说明另起一行。",
      items,
      "澜沧皓雅口腔门诊有限公司",
    );

    expect(parsed[0].mentionLevel).toBe("supplementary");
  });

  it("keeps the complete answer when the target appears after 500 characters", () => {
    const longIntroduction = "背景资料".repeat(130);
    const answer = `${longIntroduction}\n1. 王天佑口腔诊所\n2. 光雅口腔\n3. 某某口腔\n4. 另一家口腔\n5. 本地口腔\n6. 皓雅口腔门诊`;
    const parsed = parseMobileAnswers(`Q1：${answer}`, items, "澜沧皓雅口腔门诊部");

    expect(parsed[0].answerExcerpt).toBe(answer);
    expect(parsed[0].mentionLevel).toBe("supplementary");
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MobileRecommendationPlaybook } from "@/components/mobile-recommendation-playbook";

describe("mobile recommendation playbook", () => {
  it("turns a completed round into concise evidence-backed actions", () => {
    render(<MobileRecommendationPlaybook data={{
      diagnosis: {
        summary: "本轮 3 题中有 1 题补充提及、没有首批推荐。",
        mentionedCount: 1,
        totalCount: 3,
        questions: [
          { position: 1, text: "有什么值得去的口腔机构？", mentionLevel: "supplementary", mentionLabel: "补充提及", targetPosition: 5 },
          { position: 2, text: "有什么口碑好的口腔机构？", mentionLevel: "none", mentionLabel: "未提及", targetPosition: null },
        ],
      },
      competitorReasons: [{ name: "王天佑口腔诊所", questionCount: 1, reasons: [{ text: "经营多年，可使用医保", questionPositions: [1], confidence: "answer_only" }] }],
      actions: [{
        key: "name_consistency",
        title: "统一机构正式名称与常用简称",
        why: "答案使用了简称。",
        steps: ["确定正式名称", "统一公开页面"],
        materials: ["登记名称"],
        publishTargets: [{ priority: 1, channel: "高德地图、百度地图、腾讯地图", content: "统一正式名称、简称和基础资料" }],
        linkEntryHint: "发布后把公开链接粘贴到下一轮的“独立来源审计结果”。",
        examples: ["澜沧皓雅口腔门诊部（简称：皓雅口腔门诊）"],
        completionCriteria: "主要公开页面名称一致。",
        confidence: "confirmed",
      }],
      comparison: null,
      disclaimer: "建议只依据本轮答案和已确认来源。",
    }} />);

    expect(screen.getByRole("heading", { name: "推荐率提升方案" })).toBeInTheDocument();
    expect(screen.getByText(/Q1 · 补充提及 · 第 5 位/)).toBeInTheDocument();
    expect(screen.getByText("经营多年，可使用医保")).toBeInTheDocument();
    expect(screen.getByText("来自豆包回答")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "统一机构正式名称与常用简称" })).toBeInTheDocument();
    expect(screen.getByText("优先发布渠道")).toBeInTheDocument();
    expect(screen.getByText("高德地图、百度地图、腾讯地图")).toBeInTheDocument();
    expect(screen.getByText(/发布后把公开链接粘贴到下一轮/)).toBeInTheDocument();
    expect(screen.getByText(/仍用这 3 道题、3 个独立对话复测/)).toBeInTheDocument();
  });
});

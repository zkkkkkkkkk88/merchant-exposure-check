"use client";

import { useRef } from "react";

import type { MobileWorkspaceData } from "@/lib/contracts";

export function LatestMobileRoundAnswers({ answers = [] }: { answers?: MobileWorkspaceData["latestRoundAnswers"] }) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  if (!answers.length) return null;
  const collapseAnswers = () => {
    const details = detailsRef.current;
    if (!details) return;
    details.open = false;
    details.scrollIntoView?.({ block: "start" });
  };
  return <details className="latest-round-answers" ref={detailsRef}>
    <summary>查看上一轮问题与答案</summary>
    <div className="latest-round-answer-list">{answers.map((item) => <article key={item.position}>
      <header><strong>Q{item.position} · {item.question}</strong><span>{item.mentionLabel}{item.targetPosition ? ` · 第 ${item.targetPosition} 位` : ""}</span></header>
      <p>{item.answer?.trim() || "本题未保存回答内容"}</p>
    </article>)}</div>
    <div className="latest-round-collapse"><button className="button secondary" type="button" onClick={collapseAnswers}>收起答案</button></div>
  </details>;
}

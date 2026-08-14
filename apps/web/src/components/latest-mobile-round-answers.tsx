import type { MobileWorkspaceData } from "@/lib/contracts";

export function LatestMobileRoundAnswers({ answers = [] }: { answers?: MobileWorkspaceData["latestRoundAnswers"] }) {
  if (!answers.length) return null;
  return <details className="latest-round-answers">
    <summary>查看上一轮问题与答案</summary>
    <div className="latest-round-answer-list">{answers.map((item) => <article key={item.position}>
      <header><strong>Q{item.position} · {item.question}</strong><span>{item.mentionLabel}{item.targetPosition ? ` · 第 ${item.targetPosition} 位` : ""}</span></header>
      <p>{item.answer?.trim() || "本题未保存回答内容"}</p>
    </article>)}</div>
  </details>;
}

"use client";

import { useState } from "react";

export function EvidenceDrawer({ question, rawText, uncertainty, sources }: { question: string; rawText: string; uncertainty: "confirmed" | "uncertain"; sources: string[] }) {
  const [open, setOpen] = useState(false);
  return <div className="evidence-item"><div><p>{question}</p><span className={uncertainty === "uncertain" ? "evidence-label uncertain" : "evidence-label"}>{uncertainty === "uncertain" ? "待核验" : "已确认"}</span></div><button className="text-button" onClick={() => setOpen(!open)} aria-expanded={open}>查看原始证据</button>{open && <aside className="evidence-drawer" aria-label="原始证据"><h3>{question}</h3><p className="raw-answer">{rawText}</p><h4>公开来源</h4><ul>{sources.map((source) => <li key={source}><a href={source}>{source}</a></li>)}</ul><p className="evidence-warning">原始回答保持只读；“待核验”表示证据不足，不作为事实断言。</p></aside>}</div>;
}

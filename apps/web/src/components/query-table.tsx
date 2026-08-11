"use client";

import { useState } from "react";

type ReviewStatus = "pending" | "approved" | "rejected";
export interface QueryRow { id: string; text: string; category: string; reason: string; priority: number; reviewStatus: ReviewStatus; isEnabled: boolean }
const categories: Array<[string, string]> = [["all", "全部"], ["geo", "地域"], ["category", "品类"], ["product", "产品"], ["price", "价格"], ["occasion", "场景"], ["need", "需求"]];

export function QueryTable({ initialQueries }: { initialQueries: QueryRow[] }) {
  const [queries, setQueries] = useState(initialQueries);
  const [filter, setFilter] = useState("all");
  const eligible = queries.filter((item) => item.reviewStatus === "approved" && item.isEnabled).length;
  const update = (id: string, changes: Partial<QueryRow>) => setQueries((items) => items.map((item) => item.id === id ? { ...item, ...changes } : item));
  return <div className="query-workspace"><div className="query-toolbar"><div className="category-tabs" role="group" aria-label="问题分类">{categories.map(([value, label]) => <button aria-pressed={filter === value} key={value} onClick={() => setFilter(value)}>{label}</button>)}</div><button className="text-button" onClick={() => setQueries((items) => items.map((item) => item.reviewStatus === "pending" ? { ...item, reviewStatus: "approved", isEnabled: true } : item))}>批量批准待审核</button></div><p className="scan-count">可用于检测 {eligible} 条</p><div className="table-wrap"><table aria-label="待审核问题库"><thead><tr><th>问题</th><th>分类</th><th>生成理由</th><th>优先级</th><th>状态</th><th>操作</th></tr></thead><tbody>{queries.filter((item) => filter === "all" || item.category === filter).map((item) => <tr className={!item.isEnabled || item.reviewStatus === "rejected" ? "excluded-row" : ""} key={item.id}><th><input aria-label={`编辑问题 ${item.id}`} value={item.text} onChange={(event) => update(item.id, { text: event.target.value })} /></th><td>{categories.find(([value]) => value === item.category)?.[1]}</td><td>{item.reason}</td><td>{item.priority}</td><td>{item.reviewStatus === "approved" ? "已批准" : item.reviewStatus === "rejected" ? "已拒绝" : "待审核"}</td><td>{item.reviewStatus === "pending" ? <><button className="row-action" onClick={() => update(item.id, { reviewStatus: "approved", isEnabled: true })}>批准并用于检测</button><button className="row-action muted" onClick={() => update(item.id, { reviewStatus: "rejected", isEnabled: false })}>拒绝</button></> : <label className="toggle-label"><input type="checkbox" checked={item.isEnabled} onChange={(event) => update(item.id, { isEnabled: event.target.checked })} />启用</label>}</td></tr>)}</tbody></table></div></div>;
}

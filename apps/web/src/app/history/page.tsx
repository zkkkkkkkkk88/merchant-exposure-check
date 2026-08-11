import { AppShell } from "@/components/app-shell";
import { HistoryComparison } from "@/components/history-comparison";
import { getHistory, getMerchants, getScanRuns } from "@/lib/api";

export default async function HistoryPage({ searchParams = Promise.resolve({}) }: { searchParams?: Promise<{ merchant?: string }> }) {
  const params = await searchParams;
  const merchantId = params.merchant ?? (await getMerchants())[0]?.id;
  const runs = merchantId ? (await getScanRuns(merchantId)).filter((run) => run.status === "completed" || run.status === "partial") : [];
  if (!merchantId || runs.length < 2) return <AppShell><div className="workspace-page"><header className="page-header"><div><p className="kicker">HISTORY</p><h1>历史对比</h1><p>对比只使用真实完成的检测。</p></div></header><div className="state-page"><h2>至少需要两次有效检测</h2><p>当前真实数据不足，不展示模拟趋势。</p></div></div></AppShell>;
  const right = runs[0];
  const left = runs[1];
  const history = await getHistory(merchantId, left.id, right.id);
  if (!history) return <AppShell><div className="state-page"><h1>无法生成历史对比</h1></div></AppShell>;
  const label = (date: string) => new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(new Date(date));
  return <AppShell><div className="workspace-page"><header className="page-header"><div><p className="kicker">HISTORY</p><h1>历史对比</h1><p>展示最近两次真实有效检测的指标变化。</p></div></header><HistoryComparison leftLabel={label(left.finished_at ?? left.created_at)} rightLabel={label(right.finished_at ?? right.created_at)} deltas={{ mentionRate: Number(history.deltas.mention_rate ?? 0), firstPositionRate: Number(history.deltas.first_position_rate ?? 0) }} /></div></AppShell>;
}

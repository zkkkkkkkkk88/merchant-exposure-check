import { AppShell } from "@/components/app-shell";
import { HistoryComparison } from "@/components/history-comparison";

export default function HistoryPage() { return <AppShell><div className="workspace-page"><header className="page-header"><div><p className="kicker">HISTORY</p><h1>历史对比</h1><p>选择两次使用可比问题口径的检测，查看指标变化。</p></div></header><div className="period-selectors"><label>左侧检测<select defaultValue="july"><option value="july">2026-07-28 · V1</option></select></label><span>对比</span><label>右侧检测<select defaultValue="aug"><option value="aug">2026-08-11 · V1</option></select></label></div><HistoryComparison leftLabel="7月检测" rightLabel="8月检测" deltas={{ mentionRate: .12, firstPositionRate: -.04 }} /></div></AppShell>; }

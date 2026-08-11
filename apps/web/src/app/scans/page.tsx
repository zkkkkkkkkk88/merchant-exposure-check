import Link from "next/link";
import { AppShell } from "@/components/app-shell";

const runs = [{ id: "run-0811", date: "2026-08-11 09:30", status: "已完成", adapter: "火山方舟联网", result: "18 / 20" }, { id: "run-0728", date: "2026-07-28 10:15", status: "部分完成", adapter: "人工导入", result: "17 / 20" }];
export default function ScansPage() { return <AppShell><div className="workspace-page"><header className="page-header"><div><p className="kicker">SCAN RUNS</p><h1>检测记录</h1><p>每次检测绑定固定问题版本，原始回答不会被覆盖。</p></div><button className="button primary">发起新检测</button></header><div className="table-wrap"><table aria-label="检测记录"><thead><tr><th>执行时间</th><th>方式</th><th>状态</th><th>有效结果</th><th></th></tr></thead><tbody>{runs.map((run) => <tr key={run.id}><th>{run.date}</th><td>{run.adapter}</td><td>{run.status}</td><td>{run.result}</td><td><Link className="text-link" href={`/scans/${run.id}`}>查看 →</Link></td></tr>)}</tbody></table></div></div></AppShell>; }

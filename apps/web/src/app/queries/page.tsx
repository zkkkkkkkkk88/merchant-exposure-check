import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { QueryTable } from "@/components/query-table";

const queries = [
  { id: "q1", text: "杭州适合约会的西餐厅有哪些？", category: "occasion", reason: "验证约会场景关联", priority: 3, reviewStatus: "pending" as const, isEnabled: true },
  { id: "q2", text: "钱江新城人均 500 元以内餐厅推荐", category: "price", reason: "验证价格带发现", priority: 3, reviewStatus: "pending" as const, isEnabled: true },
  { id: "q3", text: "杭州万象城附近精致餐厅", category: "geo", reason: "验证地域发现", priority: 2, reviewStatus: "approved" as const, isEnabled: true },
  { id: "q4", text: "杭州季节套餐餐厅推荐", category: "product", reason: "验证产品关联", priority: 2, reviewStatus: "rejected" as const, isEnabled: false },
];
export default function QueriesPage() { return <AppShell><div className="workspace-page wide-page"><header className="page-header"><div><p className="kicker">QUERY LIBRARY / V1</p><h1>问题库</h1><p>批准的问题才会进入检测；修改会保留在当前版本。</p></div><Link className="button primary" href="/scans">进入检测</Link></header><QueryTable initialQueries={queries} /></div></AppShell>; }

import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { EvidenceDrawer } from "@/components/evidence-drawer";
import { ScanAutoRefresh } from "@/components/scan-auto-refresh";
import { ScanProgress } from "@/components/scan-progress";
import { getMerchant, getQuerySets, getScanRun } from "@/lib/api";

export default async function ScanDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const run = await getScanRun(id);
  if (!run) return <AppShell><div className="state-page"><h1>检测记录不存在</h1><Link href="/scans">返回检测记录</Link></div></AppShell>;
  const [merchant, querySets] = await Promise.all([getMerchant(run.merchant_id), getQuerySets(run.merchant_id)]);
  const queryMap = new Map(querySets.flatMap((set) => set.queries).map((query) => [query.id, query.text]));
  const selectedSet = querySets.find((set) => set.id === run.query_set_id);
  const plannedTotal = selectedSet?.queries.filter((query) => query.review_status === "approved" && query.is_enabled).length ?? 0;
  const total = Math.max(plannedTotal, run.success_count + run.failure_count);
  const isActive = run.status === "queued" || run.status === "running";
  const hasReport = run.status === "completed" || run.status === "partial";
  return (
    <AppShell>
      <div className="workspace-page">
        <ScanAutoRefresh active={isActive} />
        <header className="page-header">
          <div><p className="kicker">SCAN / {id}</p><h1>检测详情</h1><p>{merchant?.name ?? "未知商家"} · 真实原始结果</p></div>
          {hasReport && <Link className="button primary" href={`/reports/${id}`}>查看分析报告</Link>}
        </header>
        <ScanProgress status={run.status} successCount={run.success_count} failureCount={run.failure_count} totalCount={total} />
        <section className="evidence-section">
          <h2>逐题证据</h2>
          {run.results.length ? run.results.map((result) => (
            <EvidenceDrawer
              key={result.id}
              question={queryMap.get(result.query_id) ?? result.query_id}
              rawText={result.raw_text ?? result.error_message ?? "该题没有返回内容。"}
              uncertainty={result.status === "success" ? "confirmed" : "uncertain"}
              sources={result.citations.map((citation) => citation.url)}
            />
          )) : <p className="method-copy">检测尚未产生结果。</p>}
        </section>
      </div>
    </AppShell>
  );
}

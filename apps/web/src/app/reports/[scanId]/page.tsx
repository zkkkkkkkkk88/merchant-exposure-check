import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { MetricStrip } from "@/components/metric-strip";
import { getMerchant, getReport, getScanRun } from "@/lib/api";

export default async function ReportPage({ params }: { params: Promise<{ scanId: string }> }) {
  const { scanId } = await params;
  const run = await getScanRun(scanId);
  if (!run) return <AppShell><div className="state-page"><h1>报告不存在</h1><Link href="/scans">返回检测记录</Link></div></AppShell>;
  const [merchant, report] = await Promise.all([getMerchant(run.merchant_id), getReport(run.merchant_id, scanId)]);
  if (!report) return <AppShell><div className="state-page"><h1>报告尚未生成</h1><Link href={`/scans/${scanId}`}>查看检测详情</Link></div></AppShell>;
  const metrics = report.metrics;
  return (
    <AppShell>
      <div className="workspace-page">
        <header className="page-header">
          <div><p className="kicker">VISIBILITY DOSSIER / {scanId}</p><h1>可见性诊断报告</h1><p>{merchant?.name ?? "未知商家"} · {new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(new Date(run.finished_at ?? run.created_at))}</p></div>
          <Link className="button secondary" href={`/scans/${scanId}`}>返回原始结果</Link>
        </header>
        <MetricStrip metrics={{ mentionRate: Number(metrics.mention_rate), visibilityStage: metrics.visibility_stage, readinessScore: Number(metrics.readiness_score), profileCompleteness: Number(metrics.profile_completeness), publicVerifiability: Number(metrics.public_verifiability), highIntentHitRate: Number(metrics.high_intent_hit_rate), competitorGapClosure: Number(metrics.competitor_gap_closure), sourceCoverageRate: Number(metrics.source_coverage_rate), validQueryCount: metrics.valid_query_count, totalQueryCount: metrics.total_query_count }} />
        <div className="report-sections">
          <section>
            <p className="kicker">EVIDENCE FINDINGS</p><h2>基于本次扫描的发现</h2>
            {report.findings.length ? report.findings.map((finding, index) => <article className="finding-row" key={index}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{String(finding.title ?? "检测发现")}</strong><p>{String(finding.description ?? "")}</p></div></article>) : <p className="method-copy">本次扫描没有生成可确认的行动建议。</p>}
          </section>
          <section><p className="kicker">BOUNDARY</p><h2>结论边界</h2><p className="method-copy">本报告来自真实联网回答，仅描述本次问题样本，不代表平台内部排名，也不补写缺少证据的事实。</p></section>
        </div>
      </div>
    </AppShell>
  );
}

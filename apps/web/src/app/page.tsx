import Link from "next/link";

import { ActionList } from "@/components/action-list";
import { AppShell } from "@/components/app-shell";
import { CategoryCoverage } from "@/components/category-coverage";
import { CompetitorTable } from "@/components/competitor-table";
import { ExposureTrend } from "@/components/exposure-trend";
import { VisibilityStage } from "@/components/visibility-stage";
import { MetricStrip } from "@/components/metric-strip";
import { MerchantSwitcher } from "@/components/merchant-switcher";
import { ApiError, getDashboard, getMerchants } from "@/lib/api";
import type { DashboardData } from "@/lib/contracts";

export default async function DashboardPage({ searchParams = Promise.resolve({}) }: { searchParams?: Promise<{ merchant?: string }> }) {
  const params = await searchParams;
  let merchant = params.merchant;
  let data: DashboardData | null = null;
  let merchants: Awaited<ReturnType<typeof getMerchants>> = [];
  let error: string | null = null;
  try {
    merchants = await getMerchants();
    if (!merchant) merchant = merchants[0]?.id;
    if (merchant) data = await getDashboard(merchant);
  } catch (reason) { error = reason instanceof ApiError ? reason.message : "暂时无法读取检测数据。"; }
  if (error) return <AppShell><div className="state-page"><p className="kicker">DATA UNAVAILABLE</p><h1>数据读取失败</h1><p>{error}</p><Link className="button primary" href={merchant ? `/?merchant=${merchant}` : "/"}>重新加载</Link></div></AppShell>;
  if (!data) return <AppShell><div className="state-page"><p className="kicker">START HERE</p><h1>创建第一个商家后开始检测</h1><Link className="button primary" href="/merchants/new">创建商家</Link></div></AppShell>;
  return <AppShell><div className="dashboard"><header className="dashboard-header"><div><p className="kicker">VISIBILITY DOSSIER / OVERVIEW</p><h1>{data.merchant.name}</h1><p className="merchant-meta">{data.merchant.branchName ?? "全部门店"} · 最近检测 {new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(data.lastRunAt))}</p></div><div className="header-actions"><MerchantSwitcher merchants={merchants} merchantId={data.merchant.id} /><Link className="button primary" href={`/scans?merchant=${data.merchant.id}`}>发起新检测</Link></div></header><section className="metric-section-heading"><div><p className="kicker">ARK PRECHECK</p><h2>方舟联网检测</h2><p>用于批量预检和趋势参考，不代表手机版豆包结果。</p></div><Link className="button secondary" href={`/mobile-checks?merchant=${data.merchant.id}`}>进入手机版豆包实测</Link></section><VisibilityStage stage={data.metrics.visibilityStage} /><MetricStrip metrics={data.metrics} /><div className="dashboard-grid primary-grid"><ExposureTrend trend={data.trend} /><ActionList actions={data.actions} merchantId={data.merchant.id} /></div><div className="dashboard-grid secondary-grid"><CategoryCoverage categories={data.categories} /><CompetitorTable competitors={data.competitors} merchantId={data.merchant.id} /></div><footer className="method-note"><strong>方法说明</strong><p>结果来自已审核问题的公开联网回答，用来判断公开信息是否完整、可验证，以及是否进入相关回答；不代表平台内部排名。每条结论均应回到原始回答与来源核验。</p><Link href="/methodology">查看口径</Link></footer></div></AppShell>;
}

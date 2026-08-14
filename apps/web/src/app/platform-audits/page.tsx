import { createPlatformAudit } from "./actions";
import { AppShell } from "@/components/app-shell";
import { MerchantSwitcher } from "@/components/merchant-switcher";
import { PlatformAuditMatrix } from "@/components/platform-audit-matrix";
import { getLatestPlatformAudit, getMerchants } from "@/lib/api";

export default async function PlatformAuditsPage({ searchParams = Promise.resolve({}) }: { searchParams?: Promise<{ merchant?: string }> }) {
  const { merchant: requested } = await searchParams;
  const merchants = await getMerchants();
  if (!requested) return <AppShell><div className="state-page"><h1>请先选择目标商家</h1><p>平台查缺必须绑定明确商家，避免核实错对象。</p><MerchantSwitcher merchants={merchants} merchantId="" /></div></AppShell>;
  const selected = merchants.find((item) => item.id === requested);
  if (!selected) return <AppShell><div className="state-page"><h1>目标商家不存在</h1><MerchantSwitcher merchants={merchants} merchantId="" /></div></AppShell>;
  const audit = await getLatestPlatformAudit(requested);
  return <AppShell><div className="workspace-page wide-page"><header className="page-header"><div><p className="kicker">PLATFORM AUDIT</p><h1>公开平台信息查缺</h1><p>当前商家：{selected.name} · 系统查缺，人工补漏</p></div><MerchantSwitcher merchants={merchants} merchantId={requested} /></header>
    {!audit ? <section className="workspace-card audit-empty"><h2>还没有平台查缺记录</h2><p>启动后会逐项核实地图、官网公开页、短视频公开内容、登记和招聘信息。</p><form action={createPlatformAudit}><input name="merchantId" type="hidden" value={requested} /><button className="button primary" type="submit">开始公开信息查缺</button></form></section> : <><div className="audit-toolbar"><p>最近创建：{new Date(audit.created_at).toLocaleString("zh-CN")}</p><form action={createPlatformAudit}><input name="merchantId" type="hidden" value={requested} /><button className="button secondary" type="submit">重新查缺</button></form></div><PlatformAuditMatrix merchantId={requested} run={audit} /></>}
  </div></AppShell>;
}

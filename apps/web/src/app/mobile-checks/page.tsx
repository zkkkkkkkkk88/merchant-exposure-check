import { AppShell } from "@/components/app-shell";
import { MerchantSwitcher } from "@/components/merchant-switcher";
import { MobileCheckWorkspace } from "@/components/mobile-check-workspace";
import { getMerchants, getMobileValidationSets, getMobileWorkspace, getQuerySets } from "@/lib/api";

export default async function MobileChecksPage({ searchParams = Promise.resolve({}) }: { searchParams?: Promise<{ merchant?: string }> }) {
  const { merchant: requested } = await searchParams;
  const merchants = await getMerchants();
  if (!requested) {
    return <AppShell><div className="state-page"><h1>请先选择目标商家</h1><p>手机版豆包验证不会自动选择第一家，避免检测错对象。</p>{merchants.length > 0 && <MerchantSwitcher merchants={merchants} merchantId="" />}</div></AppShell>;
  }
  const selected = merchants.find((item) => item.id === requested);
  if (!selected) return <AppShell><div className="state-page"><h1>目标商家不存在</h1><p>请重新选择商家。</p><MerchantSwitcher merchants={merchants} merchantId="" /></div></AppShell>;
  const [sets, workspace, querySets] = await Promise.all([getMobileValidationSets(requested), getMobileWorkspace(requested), getQuerySets(requested)]);
  const candidates = (querySets[0]?.queries ?? []).filter((query) => query.review_status === "approved" && query.is_enabled && (query.intent_type ?? "recommendation") === "recommendation");
  const empty = { latestRoundId: null, sourceRoundId: null, metrics: null, entities: [selected.name], sourceGaps: [], recommendationPlaybook: null };
  return <AppShell><div className="workspace-page wide-page"><header className="page-header"><div><p className="kicker">MOBILE VALIDATION</p><h1>手机版豆包实测</h1><p>当前商家：{selected.name} · 3个独立对话</p></div><MerchantSwitcher merchants={merchants} merchantId={requested} /></header><MobileCheckWorkspace candidates={candidates} merchantId={requested} merchantName={selected.name} validationSet={sets.at(-1) ?? null} workspace={workspace ?? empty} /></div></AppShell>;
}

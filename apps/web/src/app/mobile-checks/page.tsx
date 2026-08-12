import { AppShell } from "@/components/app-shell";
import { MerchantSwitcher } from "@/components/merchant-switcher";
import { MobileCheckWorkspace } from "@/components/mobile-check-workspace";
import { getMerchants, getMobileValidationSets, getMobileWorkspace } from "@/lib/api";

export default async function MobileChecksPage({ searchParams = Promise.resolve({}) }: { searchParams?: Promise<{ merchant?: string }> }) {
  const { merchant: requested } = await searchParams;
  const merchants = await getMerchants();
  const merchantId = requested ?? merchants[0]?.id;
  if (!merchantId) return <AppShell><div className="state-page"><h1>手机版豆包实测</h1><p>请先创建商家。</p></div></AppShell>;
  const [sets, workspace] = await Promise.all([getMobileValidationSets(merchantId), getMobileWorkspace(merchantId)]);
  const empty = { latestRoundId: null, sourceRoundId: null, metrics: null, entities: [merchants.find((item) => item.id === merchantId)?.name ?? "目标商家"], sourceGaps: [] };
  return <AppShell><div className="workspace-page wide-page"><header className="page-header"><div><p className="kicker">MOBILE VALIDATION</p><h1>手机版豆包实测</h1><p>与方舟联网检测分开统计</p></div><MerchantSwitcher merchants={merchants} merchantId={merchantId} /></header><MobileCheckWorkspace merchantId={merchantId} validationSet={sets.at(-1) ?? null} workspace={workspace ?? empty} /></div></AppShell>;
}

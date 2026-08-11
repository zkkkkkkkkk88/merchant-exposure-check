import { AppShell } from "@/components/app-shell";
import { MerchantCreatePanel } from "@/components/merchant-create-panel";

export default function NewMerchantPage() {
  return <AppShell><div className="workspace-page narrow-page"><header className="page-header"><div><p className="kicker">NEW MERCHANT</p><h1>录入商家资料</h1><p>先记录可核验事实，再据此生成检测问题。没有把握的字段可以留空。</p></div></header><MerchantCreatePanel /></div></AppShell>;
}

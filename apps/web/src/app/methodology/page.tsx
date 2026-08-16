import { AppShell } from "@/components/app-shell";

export default function MethodologyPage() {
  return (
    <AppShell>
      <article className="workspace-page narrow-page methodology-page">
        <header className="page-header">
          <div><p className="kicker">METHODOLOGY</p><h1>检测与指标口径</h1><p>说明系统能证明什么、不能证明什么。</p></div>
        </header>
        <section><h2>方舟联网检测</h2><p>用于批量预检公开信息是否能被回答引用，不等同于手机版豆包的固定推荐结果。</p></section>
        <section><h2>手机版豆包实测</h2><p>每轮固定使用3个独立新对话。首批推荐、补充提及和未提及均以用户保存的原始回答为准。</p></section>
        <section><h2>平台查缺</h2><p>“未检索到”只表示本轮没有找到可确认的公开页面，不等于商家一定没有发布。</p></section>
        <section><h2>同题复测</h2><p>只有最新两轮使用相同问题，系统才生成前后对比，避免不同问题造成错误趋势。</p></section>
        <section><h2>结论边界</h2><p>本项目提供公开信息诊断和行动建议，不代表豆包官方排序规则，也不承诺未来每次回答都会推荐目标商家。</p></section>
      </article>
    </AppShell>
  );
}

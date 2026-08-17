import type { MobileWorkspaceData } from "@/lib/contracts";

type ChannelMaintenanceData = NonNullable<MobileWorkspaceData["channelMaintenance"]>;

export function PublicChannelMaintenance({ data }: { data: ChannelMaintenanceData }) {
  return (
    <section className="report-channel-maintenance" aria-label="公开信息渠道维护清单">
      <header>
        <h3>公开信息渠道维护清单</h3>
        <p>根据本轮已确认的公开来源整理，实际引用与候选维护渠道分开展示。</p>
      </header>

      <div className="report-channel-block">
        <h4>本轮实际引用</h4>
        {data.citedChannels.length > 0 ? (
          <div className="report-cited-channel-grid">
            {data.citedChannels.map((channel) => (
              <article key={channel.domain}>
                <header>
                  <strong>{channel.domain}</strong>
                  <span className={`report-channel-badge ${channel.access}`}>{channel.accessLabel}</span>
                </header>
                <p>引用 {channel.citationCount} 次 · {channel.sourceTypes.join("、")}</p>
                {channel.links.length > 0 && (
                  <ul>
                    {channel.links.map((link) => (
                      <li key={link.url}>
                        <a href={link.url} target="_blank" rel="noreferrer">{link.title}</a>
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            ))}
          </div>
        ) : <p className="report-empty">本轮没有可确认域名的实际引用来源。</p>}
      </div>

      <div className="report-channel-block">
        <h4>候选维护渠道</h4>
        {data.candidateChannels.length > 0 ? (
          <ul className="report-candidate-channel-list">
            {data.candidateChannels.map((candidate) => (
              <li key={candidate.channel}>
                <strong>{candidate.channel}</strong>
                <span>{candidate.content}</span>
              </li>
            ))}
          </ul>
        ) : <p className="report-empty">本轮暂无额外候选维护渠道。</p>}
      </div>

      <div className="report-channel-guidance">
        <p><strong>统一信息要求：</strong>商家名称、城市、品类、地址、电话和核心服务保持一致。</p>
        <p>完善公开信息可以提高被检索和正确引用的概率，但不保证进入首批推荐。</p>
      </div>
    </section>
  );
}

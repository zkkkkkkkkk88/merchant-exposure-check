"use client";

import type { MobileSourceDiscoveryData } from "@/lib/contracts";

const sourceTypeLabels: Record<string, string> = {
  profile: "机构或地图页面",
  registry: "登记信息",
  recruitment: "招聘页面",
  douyin: "抖音公开内容",
  local_media: "本地媒体",
  government: "政府公开页面",
  industry: "行业页面",
  other: "其他公开页面",
};

type Props = {
  groups: MobileSourceDiscoveryData["groups"];
  loading: boolean;
  error: string | null;
  hasSearched: boolean;
  onDiscover: () => void;
};

export function MobileSourceReview({
  groups,
  loading,
  error,
  hasSearched,
  onDiscover,
}: Props) {
  const sourceCount = groups.reduce((total, group) => total + group.sources.length, 0);
  return (
    <section className="mobile-source-review" aria-label="公开来源自动查找">
      <div className="mobile-source-review-header">
        <div>
          <h3>公开来源自动查找</h3>
          <p>系统先查找，只有你勾选确认的来源才会计入本轮审计。</p>
        </div>
        <button
          className="button secondary"
          disabled={loading}
          onClick={onDiscover}
          type="button"
        >
          {loading ? "正在查找…" : hasSearched ? "重新查找" : "自动查找公开来源"}
        </button>
      </div>

      {error && <p className="form-guidance source-discovery-error">{error}</p>}
      {hasSearched && sourceCount === 0 && !loading && (
        <p className="source-discovery-empty">
          本次未找到可核验来源，不代表商家没有发布。你可以稍后重试或手工补充。
        </p>
      )}
      {groups.map((group) => (
        <article className="source-entity-group" key={group.entity_name}>
          <header>
            <h4>{group.entity_name}</h4>
            <span>{group.sources.length} 条候选来源</span>
          </header>
          {group.error && <p className="source-group-error">{group.error}</p>}
          <div className="source-candidate-list">
            {group.sources.map((source) => (
              <label className="source-candidate" key={`${source.entity_name}:${source.url}`}>
                <input
                  name="confirmedAutoSources"
                  type="checkbox"
                  value={JSON.stringify(source)}
                />
                <span className="source-candidate-copy">
                  <strong>{source.title}</strong>
                  <small>{sourceTypeLabels[source.source_type] ?? "公开页面"}</small>
                  {source.facts.length > 0 && <span>{source.facts.join("；")}</span>}
                </span>
                <a href={source.url} onClick={(event) => event.stopPropagation()} rel="noreferrer" target="_blank">
                  查看来源
                </a>
              </label>
            ))}
          </div>
        </article>
      ))}

      <details className="manual-source-entry">
        <summary>手工补充来源</summary>
        <p>自动查找有遗漏时再补充，每个来源占一行。</p>
        <textarea
          name="manualSources"
          placeholder="机构｜来源类型｜标题｜事实｜网址"
          rows={5}
        />
      </details>
    </section>
  );
}

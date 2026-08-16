import type { MobileAnswerDraft } from "./mobile-answer-parser";
import type { MobileSourceCandidateData } from "./contracts";

export type CompetitorOccurrenceData = {
  name: string;
  occurrence_count: number;
};

function entityCore(value: string): string {
  return value
    .normalize("NFKC")
    .replace(/[\s（）()·]/g, "")
    .replace(/(?:口腔医疗机构|口腔门诊部|口腔门诊|门诊部|诊所|医院|口腔)$/u, "")
    .toLocaleLowerCase("zh-CN");
}

export function countRecurringCompetitors(
  drafts: MobileAnswerDraft[],
  merchantName: string,
): CompetitorOccurrenceData[] {
  const targetCore = entityCore(merchantName);
  const counts = new Map<string, { name: string; count: number; first: number }>();
  let sequence = 0;
  for (const answer of drafts) {
    const seenInAnswer = new Set<string>();
    for (const rawName of answer.competitors) {
      const name = rawName.trim();
      const core = entityCore(name);
      if (!core || core === targetCore || seenInAnswer.has(core)) continue;
      seenInAnswer.add(core);
      const current = counts.get(core);
      if (current) current.count += 1;
      else counts.set(core, { name, count: 1, first: sequence++ });
    }
  }
  return [...counts.values()]
    .filter((item) => item.count >= 2)
    .sort((left, right) => right.count - left.count || left.first - right.first)
    .slice(0, 3)
    .map((item) => ({ name: item.name, occurrence_count: item.count }));
}

export type ConfirmedMobileSource = Omit<MobileSourceCandidateData, "reused_from_audit"> & {
  is_confirmed: true;
};

const manualSourceTypes: Record<string, MobileSourceCandidateData["source_type"]> = {
  机构介绍: "profile",
  工商: "registry",
  招聘: "recruitment",
  抖音: "douyin",
  本地媒体: "local_media",
  政府医院: "government",
  行业内容: "industry",
};

const allowedSourceTypes = new Set<MobileSourceCandidateData["source_type"]>([
  "profile",
  "registry",
  "recruitment",
  "douyin",
  "local_media",
  "government",
  "industry",
  "other",
]);

function validHttpUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value.trim());
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function automaticSource(value: string): ConfirmedMobileSource | null {
  try {
    const parsed = JSON.parse(value) as Partial<MobileSourceCandidateData>;
    const url = validHttpUrl(parsed.url);
    if (!url || !parsed.entity_name?.trim() || !parsed.title?.trim()) return null;
    const sourceType = allowedSourceTypes.has(parsed.source_type as MobileSourceCandidateData["source_type"])
      ? parsed.source_type as MobileSourceCandidateData["source_type"]
      : "other";
    return {
      entity_name: parsed.entity_name.trim(),
      source_type: sourceType,
      title: parsed.title.trim(),
      facts: Array.isArray(parsed.facts) ? parsed.facts.filter((fact): fact is string => typeof fact === "string") : [],
      url,
      evidence_kind: parsed.evidence_kind === "official" ? "official" : "third_party",
      access_status: parsed.access_status === "correctable" ? "correctable" : "reference",
      is_confirmed: true,
    };
  } catch {
    return null;
  }
}

function manualSource(line: string): ConfirmedMobileSource | null {
  const [entityName, rawType, title, rawFacts, rawUrl] = line
    .split("｜")
    .map((item) => item.trim());
  const url = validHttpUrl(rawUrl);
  if (!entityName || !title || !url) return null;
  return {
    entity_name: entityName,
    source_type: manualSourceTypes[rawType] ?? "other",
    title,
    facts: rawFacts ? rawFacts.split(/[、,，]/).map((item) => item.trim()).filter(Boolean) : [],
    url,
    evidence_kind: "third_party",
    access_status: "reference",
    is_confirmed: true,
  };
}

export function mergeConfirmedSources(
  automaticValues: string[],
  manualText: string,
): ConfirmedMobileSource[] {
  const candidates = [
    ...automaticValues.map(automaticSource),
    ...manualText.split(/\r?\n/).map((line) => manualSource(line.trim())),
  ];
  const sources: ConfirmedMobileSource[] = [];
  const seen = new Set<string>();
  for (const candidate of candidates) {
    if (!candidate || seen.has(candidate.url)) continue;
    seen.add(candidate.url);
    sources.push(candidate);
  }
  return sources;
}

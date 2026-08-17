import type { DashboardData, MobileWorkspaceData } from "@/lib/contracts";

export type PublicChannelMaintenanceData = NonNullable<MobileWorkspaceData["channelMaintenance"]>;

const scanAccess = (
  access: DashboardData["actions"][number]["sourceChannels"][number]["access"],
): PublicChannelMaintenanceData["citedChannels"][number]["access"] => (
  access === "submission" ? "correctable" : access
);

export function buildPublicChannelMaintenance(
  mobileData: MobileWorkspaceData["channelMaintenance"] | undefined,
  scanActions: DashboardData["actions"],
): PublicChannelMaintenanceData {
  const cited = new Map<string, PublicChannelMaintenanceData["citedChannels"][number]>();

  for (const action of scanActions) {
    for (const source of action.sourceChannels) {
      const existing = cited.get(source.domain);
      if (existing) {
        existing.citationCount += source.citationCount;
        continue;
      }
      cited.set(source.domain, {
        domain: source.domain,
        citationCount: source.citationCount,
        access: scanAccess(source.access),
        accessLabel: source.label,
        sourceTypes: ["检测回答引用来源"],
        links: [],
      });
    }
  }

  for (const source of mobileData?.citedChannels ?? []) {
    const existing = cited.get(source.domain);
    if (!existing) {
      cited.set(source.domain, {
        ...source,
        sourceTypes: [...source.sourceTypes],
        links: [...source.links],
      });
      continue;
    }
    existing.sourceTypes = Array.from(new Set([...existing.sourceTypes, ...source.sourceTypes]));
    existing.links = Array.from(
      new Map([...existing.links, ...source.links].map((link) => [link.url, link])).values(),
    ).slice(0, 2);
  }

  const candidateChannels: PublicChannelMaintenanceData["candidateChannels"] = [];
  const seenCandidates = new Set<string>();
  const addCandidate = (channel: string, content: string) => {
    const name = channel.trim();
    if (!name || seenCandidates.has(name)) return;
    seenCandidates.add(name);
    candidateChannels.push({ channel: name, content: content.trim() });
  };
  for (const candidate of mobileData?.candidateChannels ?? []) {
    addCandidate(candidate.channel, candidate.content);
  }
  for (const action of scanActions) {
    for (const channel of action.channels) addCandidate(channel, action.description);
  }

  return {
    citedChannels: Array.from(cited.values()),
    candidateChannels,
  };
}

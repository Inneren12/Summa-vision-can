import type { DistributionJson } from './distributionJson';

export interface BuildPublishKitTxtOptions {
  distribution: DistributionJson;
}

export function buildPublishKitTxt(options: BuildPublishKitTxtOptions): string {
  const { distribution } = options;
  const sections = [
    ['Reddit', distribution.channels.reddit],
    ['X / Twitter', distribution.channels.twitter],
    ['LinkedIn', distribution.channels.linkedin],
  ] as const;

  return `${sections
    .map(([label, channel]) => `=== ${label} ===\n${channel.caption}\n${channel.share_url}`)
    .join('\n\n')}\n`;
}

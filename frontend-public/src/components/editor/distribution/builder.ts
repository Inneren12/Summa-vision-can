import type { PlatformId } from '../types';
import { distributionTemplates } from './templates';

export interface BuildChannelCaptionOptions {
  platform: PlatformId;
  headline: string;
  shareUrl: string;
}

export function buildChannelCaption(options: BuildChannelCaptionOptions): string {
  const { platform, headline, shareUrl } = options;
  return distributionTemplates[platform]({ headline, url: shareUrl });
}

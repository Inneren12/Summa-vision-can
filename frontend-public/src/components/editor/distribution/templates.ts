export interface CaptionTemplateContext {
  headline: string;
  url: string;
}

export const distributionTemplates = {
  reddit: ({ headline, url }: CaptionTemplateContext): string =>
    `${headline}\n\nRead more: ${url}`,
  twitter: ({ headline, url }: CaptionTemplateContext): string =>
    `${headline} ${url}`,
  linkedin: ({ headline, url }: CaptionTemplateContext): string =>
    `${headline}\n\nRead the full post: ${url}`,
} as const;

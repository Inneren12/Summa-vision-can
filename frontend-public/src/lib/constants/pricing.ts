export interface SponsorshipTier {
  name: string;
  price: string;
  description: string;
  features: string[];
  highlighted: boolean;
  cta: string;
}

export const SPONSORSHIP_TIERS: SponsorshipTier[] = [
  {
    name: "Starter",
    price: "$75 CPM",
    description:
      "Perfect for testing the waters with our engaged Canadian audience.",
    features: [
      "Logo placement on 5 infographics",
      "Branded footer mention",
      "Monthly performance report",
    ],
    highlighted: false,
    cta: "Get Started",
  },
  {
    name: "Growth",
    price: "$150 CPM",
    description:
      "Maximum exposure across all our distribution channels.",
    features: [
      "Logo placement on 15 infographics",
      "Branded footer + header mention",
      "Social media co-promotion",
      "Weekly performance reports",
      "Priority placement in gallery",
    ],
    highlighted: true,
    cta: "Most Popular",
  },
  {
    name: "Enterprise",
    price: "Custom",
    description:
      "Bespoke data visualization content for your brand.",
    features: [
      "Custom infographics on your topics",
      "Exclusive data analysis",
      "White-label licensing",
      "Dedicated account manager",
      "Raw dataset access",
    ],
    highlighted: false,
    cta: "Contact Us",
  },
];

export const AUDIENCE_METRICS = {
  monthlyViews: "50,000+",
  avgEngagementRate: "4.2%",
  topSubreddits: [
    "r/canada",
    "r/canadahousing",
    "r/PersonalFinanceCanada",
  ],
  primaryPlatforms: ["Reddit", "X (Twitter)", "LinkedIn"],
  audienceDemo:
    "Canadian professionals, policy analysts, real estate investors, journalists",
};

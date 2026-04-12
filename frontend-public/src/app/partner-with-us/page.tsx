import type { Metadata } from 'next';
import { AUDIENCE_METRICS, SPONSORSHIP_TIERS } from '@/lib/constants/pricing';
import InquiryForm from '@/components/forms/InquiryForm';

export const metadata: Metadata = {
  title: 'Partner with Summa Vision | Canadian Data Visualization Sponsorship',
  description:
    'Reach 50,000+ engaged Canadians through branded data visualizations. Sponsorship tiers starting at $75 CPM.',
  openGraph: {
    title: 'Partner with Summa Vision',
    description:
      'Sponsor Canadian macro-economic data visualizations reaching policy analysts, investors, and journalists.',
    type: 'website',
  },
};

function CheckIcon() {
  return (
    <svg
      className="mt-0.5 h-5 w-5 shrink-0 text-neon-green"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

export default function PartnerPage() {
  return (
    <main className="min-h-screen bg-background">
      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="px-4 pb-16 pt-20 text-center sm:px-6 lg:px-8">
        <h1 className="mx-auto max-w-3xl text-4xl font-extrabold tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
          Partner with{' '}
          <span className="text-neon-green">Summa Vision</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-text-secondary">
          Reach engaged Canadian professionals through branded data
          visualizations covering housing, inflation, and economic trends.
        </p>
      </section>

      {/* ── Section 1: Our Audience ───────────────────────────── */}
      <section className="px-4 pb-20 sm:px-6 lg:px-8" aria-labelledby="audience-heading">
        <div className="mx-auto max-w-6xl">
          <h2
            id="audience-heading"
            className="mb-12 text-center text-3xl font-bold text-text-primary sm:text-4xl"
          >
            Our Audience
          </h2>

          {/* Stat cards row */}
          <div className="mb-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-surface p-8 text-center">
              <p className="text-4xl font-extrabold text-neon-green">
                {AUDIENCE_METRICS.monthlyViews}
              </p>
              <p className="mt-2 text-sm text-text-secondary">
                Monthly Views
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-surface p-8 text-center">
              <p className="text-4xl font-extrabold text-neon-blue">
                {AUDIENCE_METRICS.avgEngagementRate}
              </p>
              <p className="mt-2 text-sm text-text-secondary">
                Avg. Engagement Rate
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-surface p-8 text-center sm:col-span-2 lg:col-span-1">
              <p className="text-4xl font-extrabold text-neon-yellow">
                {AUDIENCE_METRICS.primaryPlatforms.length}
              </p>
              <p className="mt-2 text-sm text-text-secondary">
                Distribution Platforms
              </p>
            </div>
          </div>

          {/* Detail cards */}
          <div className="grid gap-6 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-surface p-6">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-neon-green">
                Top Communities
              </h3>
              <ul className="space-y-2">
                {AUDIENCE_METRICS.topSubreddits.map((sub) => (
                  <li
                    key={sub}
                    className="text-sm text-text-secondary"
                  >
                    {sub}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-white/10 bg-surface p-6">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-neon-blue">
                Platforms
              </h3>
              <ul className="space-y-2">
                {AUDIENCE_METRICS.primaryPlatforms.map((platform) => (
                  <li
                    key={platform}
                    className="text-sm text-text-secondary"
                  >
                    {platform}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-white/10 bg-surface p-6">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-neon-yellow">
                Demographics
              </h3>
              <p className="text-sm text-text-secondary">
                {AUDIENCE_METRICS.audienceDemo}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 2: Sponsorship Tiers ──────────────────────── */}
      <section
        className="px-4 pb-20 sm:px-6 lg:px-8"
        aria-labelledby="tiers-heading"
      >
        <div className="mx-auto max-w-6xl">
          <h2
            id="tiers-heading"
            className="mb-4 text-center text-3xl font-bold text-text-primary sm:text-4xl"
          >
            Sponsorship Tiers
          </h2>
          <p className="mx-auto mb-12 max-w-xl text-center text-text-secondary">
            Choose the tier that fits your goals. All plans include
            performance analytics and dedicated support.
          </p>

          <div className="grid gap-8 lg:grid-cols-3">
            {SPONSORSHIP_TIERS.map((tier) => (
              <div
                key={tier.name}
                data-testid="tier-card"
                className={`relative flex flex-col rounded-2xl border p-8 transition-transform hover:scale-[1.02] ${
                  tier.highlighted
                    ? 'border-neon-green/50 bg-surface shadow-[0_0_30px_rgba(0,255,148,0.1)]'
                    : 'border-white/10 bg-surface'
                }`}
              >
                {tier.highlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-neon-green px-4 py-1 text-xs font-bold text-background">
                    Most Popular
                  </span>
                )}

                <h3 className="text-xl font-bold text-text-primary">
                  {tier.name}
                </h3>
                <p className="mt-2 text-3xl font-extrabold text-neon-green">
                  {tier.price}
                </p>
                <p className="mt-3 text-sm text-text-secondary">
                  {tier.description}
                </p>

                <ul className="mt-6 flex-1 space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex gap-2 text-sm text-text-secondary">
                      <CheckIcon />
                      {feature}
                    </li>
                  ))}
                </ul>

                <a
                  href="#inquiry"
                  className={`mt-8 block rounded-lg py-3 text-center font-semibold transition-opacity hover:opacity-90 ${
                    tier.highlighted
                      ? 'bg-neon-green text-background'
                      : 'border border-neon-green/50 text-neon-green'
                  }`}
                >
                  {tier.cta}
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 3: Custom Content + Inquiry Form ──────────── */}
      <section
        id="inquiry"
        className="scroll-mt-8 px-4 pb-24 sm:px-6 lg:px-8"
        aria-labelledby="inquiry-heading"
      >
        <div className="mx-auto max-w-2xl">
          <h2
            id="inquiry-heading"
            className="mb-4 text-center text-3xl font-bold text-text-primary sm:text-4xl"
          >
            Let&apos;s Build Something Together
          </h2>
          <p className="mx-auto mb-10 max-w-lg text-center text-text-secondary">
            Interested in custom data visualizations for your brand?
            Tell us about your goals and we&apos;ll craft a bespoke
            sponsorship package.
          </p>

          <div className="rounded-2xl border border-white/10 bg-surface p-8">
            <InquiryForm />
          </div>
        </div>
      </section>
    </main>
  );
}

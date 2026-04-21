import type { Metadata } from 'next';
import dynamic from 'next/dynamic';
import { AUDIENCE_METRICS, SPONSORSHIP_TIERS } from '@/lib/constants/pricing';

// InquiryForm ships a large react-hook-form + zod import chain. The form
// is visible on initial paint (not click-gated), so keep ssr:true to
// preserve the SSR HTML for SEO / no-JS users; only hydration defers.
const InquiryForm = dynamic(() => import('@/components/forms/InquiryForm'), {
  ssr: true,
});

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
      className="mt-0.5 h-5 w-5 shrink-0 text-accent"
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
    <main className="min-h-screen bg-bg-app">
      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="px-4 pb-16 pt-20 text-center sm:px-6 lg:px-8">
        <h1 className="mx-auto max-w-3xl text-4xl font-extrabold font-display tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
          Partner with{' '}
          <span className="text-accent">Summa Vision</span>
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
            <div className="rounded-public bg-card-bg shadow-card p-8 text-center">
              <p className="text-4xl font-extrabold font-display text-text-primary">
                {AUDIENCE_METRICS.monthlyViews}
              </p>
              <p className="mt-2 text-sm text-text-secondary">
                Monthly Views
              </p>
            </div>
            <div className="rounded-public bg-card-bg shadow-card p-8 text-center">
              <p className="text-4xl font-extrabold font-display text-text-primary">
                {AUDIENCE_METRICS.avgEngagementRate}
              </p>
              <p className="mt-2 text-sm text-text-secondary">
                Avg. Engagement Rate
              </p>
            </div>
            <div className="rounded-public bg-card-bg shadow-card p-8 text-center sm:col-span-2 lg:col-span-1">
              <p className="text-4xl font-extrabold font-display text-text-primary">
                {AUDIENCE_METRICS.primaryPlatforms.length}
              </p>
              <p className="mt-2 text-sm text-text-secondary">
                Distribution Platforms
              </p>
            </div>
          </div>

          {/* Detail cards */}
          <div className="grid gap-6 md:grid-cols-3">
            <div className="rounded-public bg-card-bg shadow-card p-6">
              <h3 className="mb-3 text-sm font-semibold font-data uppercase tracking-wider text-data-positive">
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
            <div className="rounded-public bg-card-bg shadow-card p-6">
              <h3 className="mb-3 text-sm font-semibold font-data uppercase tracking-wider text-data-gov">
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
            <div className="rounded-public bg-card-bg shadow-card p-6">
              <h3 className="mb-3 text-sm font-semibold font-data uppercase tracking-wider text-data-warning">
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
                className={`relative flex flex-col rounded-public border p-8 transition-transform hover:scale-[1.02] ${
                  tier.highlighted
                    ? 'border-accent bg-card-bg shadow-[0_0_30px_var(--accent-muted)]'
                    : 'border-border-default bg-card-bg'
                }`}
              >
                {tier.highlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-accent px-4 py-1 text-xs font-bold text-text-inverse">
                    Most Popular
                  </span>
                )}

                <h3 className="text-xl font-bold text-text-primary">
                  {tier.name}
                </h3>
                <p className="mt-2 text-3xl font-extrabold font-display text-accent">
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
                  className={`mt-8 block rounded-button py-3 text-center font-semibold transition-opacity hover:opacity-90 ${
                    tier.highlighted
                      ? 'bg-accent text-text-inverse hover:bg-accent-hover'
                      : 'border border-accent/50 text-accent'
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

          <div className="rounded-public border border-border-default bg-bg-surface p-8">
            <InquiryForm />
          </div>
        </div>
      </section>
    </main>
  );
}

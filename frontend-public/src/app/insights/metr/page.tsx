import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Working More Can Cost You | Summa Vision',
  description:
    'Explore how the Marginal Effective Tax Rate creates poverty traps for Canadian families.',
};

export default function METRInsightPage() {
  return (
    <main className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-display font-extrabold text-text-primary mb-4">
        Working More Can Cost You
      </h1>
      <p className="text-lg text-text-secondary font-body mb-8">
        Canada&apos;s tax and benefit system can create poverty traps where
        earning an extra dollar costs more than it pays. The Marginal Effective
        Tax Rate (METR) reveals these hidden cliffs.
      </p>

      <section className="mb-12">
        <h2 className="text-2xl font-display font-bold text-text-primary mb-3">
          The Poverty Trap
        </h2>
        <p className="text-text-secondary font-body mb-4">
          When taxes rise and benefits claw back simultaneously, some families
          face marginal rates above 80% — keeping less than 20 cents on each
          new dollar earned. This creates a &ldquo;dead zone&rdquo; where
          working more hours results in less take-home pay.
        </p>
      </section>

      <Link
        href="/insights/metr/calculator"
        className="inline-block py-3 px-6 rounded-button bg-btn-primary-bg text-btn-primary-text font-semibold hover:opacity-90 transition-opacity"
        data-testid="calculator-cta"
      >
        Try the METR Calculator
      </Link>
    </main>
  );
}

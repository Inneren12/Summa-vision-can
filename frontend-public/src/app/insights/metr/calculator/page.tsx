import type { Metadata } from 'next';
import METRCalculator from '@/components/metr/METRCalculator';

export const metadata: Metadata = {
  title: 'METR Calculator | Summa Vision',
  description:
    'Interactive calculator showing your Marginal Effective Tax Rate across Canadian provinces.',
};

export default function METRCalculatorPage() {
  return (
    <main className="max-w-5xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-display font-extrabold text-text-primary mb-2">
        METR Calculator
      </h1>
      <p className="text-text-secondary font-body mb-8">
        See how much of your next dollar you actually keep.
      </p>
      <METRCalculator />
    </main>
  );
}

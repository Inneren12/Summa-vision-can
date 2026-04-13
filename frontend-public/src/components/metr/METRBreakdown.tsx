'use client';

import type { METRComponents } from '@/lib/types/metr';

interface METRBreakdownProps {
  components: METRComponents | null;
}

const LABELS: Record<keyof METRComponents, string> = {
  federal_tax: 'Federal Tax',
  provincial_tax: 'Provincial Tax',
  cpp: 'CPP',
  cpp2: 'CPP2',
  ei: 'EI',
  ohp: 'OHP',
  ccb: 'CCB',
  gst_credit: 'GST Credit',
  cwb: 'CWB',
  provincial_benefits: 'Provincial Benefits',
};

export default function METRBreakdown({ components }: METRBreakdownProps) {
  if (!components) return null;

  return (
    <div data-testid="metr-breakdown">
      <h3 className="font-display font-bold text-text-primary mb-2">
        Component Breakdown
      </h3>
      <dl className="space-y-1">
        {(Object.keys(LABELS) as (keyof METRComponents)[]).map((key) => (
          <div key={key} className="flex justify-between text-sm">
            <dt className="text-text-secondary font-body">{LABELS[key]}</dt>
            <dd className="font-data text-text-primary">
              {components[key].toFixed(1)}%
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

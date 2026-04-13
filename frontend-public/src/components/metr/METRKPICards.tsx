'use client';

import type { METRCalculateResponse } from '@/lib/types/metr';

interface METRKPICardsProps {
  data: METRCalculateResponse | null;
}

export default function METRKPICards({ data }: METRKPICardsProps) {
  if (!data) return null;

  return (
    <div
      className="grid grid-cols-2 gap-4 md:grid-cols-3"
      data-testid="metr-kpi-cards"
    >
      <div className="rounded-public bg-card-bg p-4 shadow-card">
        <p className="text-xs text-text-secondary font-body">METR</p>
        <p className="text-2xl font-display font-bold text-text-primary" data-testid="kpi-metr">
          {data.metr.toFixed(1)}%
        </p>
      </div>
      <div className="rounded-public bg-card-bg p-4 shadow-card">
        <p className="text-xs text-text-secondary font-body">Net Income</p>
        <p className="text-2xl font-display font-bold text-text-primary" data-testid="kpi-net-income">
          ${data.net_income.toLocaleString()}
        </p>
      </div>
      <div className="rounded-public bg-card-bg p-4 shadow-card">
        <p className="text-xs text-text-secondary font-body">Keep per Dollar</p>
        <p className="text-2xl font-display font-bold text-text-primary" data-testid="kpi-keep">
          {(data.keep_per_dollar * 100).toFixed(0)}&cent;
        </p>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';

export default function MethodologyDrawer() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div data-testid="methodology-drawer">
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="text-accent text-sm font-body underline"
        data-testid="methodology-toggle"
      >
        How is METR calculated?
      </button>
      {isOpen && (
        <div
          className="mt-4 p-4 rounded-public bg-bg-surface border border-border-default"
          role="region"
          aria-label="METR methodology"
          data-testid="methodology-content"
        >
          <h3 className="font-display font-bold text-text-primary mb-2">
            Methodology
          </h3>
          <p className="text-sm text-text-secondary font-body">
            The Marginal Effective Tax Rate (METR) measures the combined impact
            of income taxes, payroll deductions (CPP, EI), and the clawback of
            income-tested benefits (CCB, GST Credit, CWB) on each additional
            dollar of employment income. A METR above 50% means a worker keeps
            less than half of their next dollar earned.
          </p>
        </div>
      )}
    </div>
  );
}

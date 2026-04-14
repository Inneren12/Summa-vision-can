'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchMETRCalculation, fetchMETRCurve } from '@/lib/api/metr';
import type {
  FamilyType,
  METRCalculateResponse,
  METRCurveResponse,
  Province,
} from '@/lib/types/metr';
import METRChart from './METRChart';
import METRKPICards from './METRKPICards';
import METRBreakdown from './METRBreakdown';
import MethodologyDrawer from './MethodologyDrawer';

const PROVINCES: { value: Province; label: string }[] = [
  { value: 'ON', label: 'Ontario' },
  { value: 'BC', label: 'British Columbia' },
  { value: 'AB', label: 'Alberta' },
  { value: 'QC', label: 'Quebec' },
];

const FAMILY_TYPES: { value: FamilyType; label: string }[] = [
  { value: 'single', label: 'Single, no children' },
  { value: 'single_parent', label: 'Single parent' },
  { value: 'couple', label: 'Couple' },
];

export default function METRCalculator() {
  const [income, setIncome] = useState(50000);
  const [province, setProvince] = useState<Province>('ON');
  const [familyType, setFamilyType] = useState<FamilyType>('single');
  const [nChildren, setNChildren] = useState(0);
  const [childrenUnder6, setChildrenUnder6] = useState(0);

  const [calcData, setCalcData] = useState<METRCalculateResponse | null>(null);
  const [curveData, setCurveData] = useState<METRCurveResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [calc, curve] = await Promise.all([
        fetchMETRCalculation({
          income,
          province,
          family_type: familyType,
          n_children: nChildren,
          children_under_6: childrenUnder6,
        }),
        fetchMETRCurve({
          province,
          family_type: familyType,
          n_children: nChildren,
          children_under_6: childrenUnder6,
        }),
      ]);
      setCalcData(calc);
      setCurveData(curve);
    } catch (err) {
      console.error('METR calculation failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to load METR data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [income, province, familyType, nChildren, childrenUnder6]);

  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      loadData();
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [income, province, familyType, nChildren, childrenUnder6]);

  return (
    <div className="space-y-6" data-testid="metr-calculator">
      {/* Controls */}
      <div
        className="flex flex-col gap-4 md:flex-row md:items-end"
        data-testid="calculator-controls"
      >
        {/* Income slider */}
        <div className="flex-1">
          <label
            htmlFor="income-slider"
            className="block text-sm text-text-secondary font-body mb-1"
          >
            Gross Income
          </label>
          <input
            id="income-slider"
            type="range"
            min={0}
            max={200000}
            step={1000}
            value={income}
            onChange={(e) => setIncome(Number(e.target.value))}
            className="w-full"
            aria-label="Income slider"
          />
          <p className="text-sm font-data text-text-primary mt-1" data-testid="income-display">
            ${income.toLocaleString()}
          </p>
        </div>

        {/* Province selector */}
        <div>
          <label
            htmlFor="province-select"
            className="block text-sm text-text-secondary font-body mb-1"
          >
            Province
          </label>
          <select
            id="province-select"
            value={province}
            onChange={(e) => setProvince(e.target.value as Province)}
            className="px-3 py-2 rounded-public border border-border-default bg-bg-app text-text-primary"
            aria-label="Province selector"
          >
            {PROVINCES.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        {/* Family type selector */}
        <div>
          <label
            htmlFor="family-type-select"
            className="block text-sm text-text-secondary font-body mb-1"
          >
            Family Type
          </label>
          <select
            id="family-type-select"
            value={familyType}
            onChange={(e) => setFamilyType(e.target.value as FamilyType)}
            className="px-3 py-2 rounded-public border border-border-default bg-bg-app text-text-primary"
            aria-label="Family type selector"
          >
            {FAMILY_TYPES.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </div>

        {/* Children stepper */}
        <div>
          <label
            htmlFor="children-stepper"
            className="block text-sm text-text-secondary font-body mb-1"
          >
            Children
          </label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setNChildren((n) => {
                  const next = Math.max(0, n - 1);
                  setChildrenUnder6((u6) => Math.min(u6, next));
                  return next;
                });
              }}
              aria-label="Decrease children"
              className="px-2 py-1 rounded-button border border-border-default text-text-primary"
            >
              &minus;
            </button>
            <span
              className="font-data text-text-primary w-8 text-center"
              aria-label="Children count"
              data-testid="children-count"
            >
              {nChildren}
            </span>
            <button
              type="button"
              onClick={() => setNChildren((n) => Math.min(6, n + 1))}
              aria-label="Increase children"
              className="px-2 py-1 rounded-button border border-border-default text-text-primary"
            >
              +
            </button>
          </div>
        </div>

        {/* Children under 6 stepper — visible when nChildren > 0 */}
        {nChildren > 0 && (
          <div>
            <label
              htmlFor="children-under6-stepper"
              className="block text-sm text-text-secondary font-body mb-1"
            >
              Children under 6
            </label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setChildrenUnder6((n) => Math.max(0, n - 1))}
                aria-label="Decrease children under 6"
                className="px-2 py-1 rounded-button border border-border-default text-text-primary"
              >
                &minus;
              </button>
              <span
                className="font-data text-text-primary w-8 text-center"
                aria-label="Children under 6 count"
                data-testid="children-under6-count"
              >
                {childrenUnder6}
              </span>
              <button
                type="button"
                onClick={() => setChildrenUnder6((n) => Math.min(nChildren, n + 1))}
                aria-label="Increase children under 6"
                className="px-2 py-1 rounded-button border border-border-default text-text-primary"
              >
                +
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-destructive/10 border border-destructive rounded-public p-md text-destructive">
          {error}
          <button
            type="button"
            onClick={() => { setError(null); loadData(); }}
            className="ml-md text-accent underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state — skeleton loader */}
      {loading && (
        <div data-testid="skeleton-loader" className="space-y-4 animate-pulse">
          <div className="h-8 bg-bg-surface rounded w-1/3" />
          <div className="h-64 bg-bg-surface rounded" />
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <div className="h-20 bg-bg-surface rounded" />
            <div className="h-20 bg-bg-surface rounded" />
            <div className="h-20 bg-bg-surface rounded" />
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && curveData && (
        <METRChart curve={curveData.curve} deadZones={curveData.dead_zones} />
      )}

      {!loading && calcData && (
        <>
          <METRKPICards data={calcData} />
          <METRBreakdown components={calcData.components} />
        </>
      )}

      <MethodologyDrawer />
    </div>
  );
}

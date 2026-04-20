'use client';

/**
 * Web Vitals reporting hook (Stage 4 Task 9a — Batch A).
 *
 * Integrates with Next.js's built-in `useReportWebVitals` hook from
 * `next/web-vitals`. Metrics collected:
 *   - LCP  (Largest Contentful Paint)      — loading perf
 *   - INP  (Interaction to Next Paint)     — responsiveness
 *   - CLS  (Cumulative Layout Shift)       — visual stability
 *   - FCP  (First Contentful Paint)        — paint timing
 *   - TTFB (Time to First Byte)            — network timing
 *
 * Dev mode: logs to console with a `[web-vitals]` prefix.
 * Production: currently a no-op. Hook is in place for future CI /
 * analytics integration; no endpoint wired today.
 *
 * This module must be imported from a client component (via the
 * WebVitalsReporter component below). Calling useReportWebVitals
 * from a server component is a no-op.
 */

import { useReportWebVitals } from 'next/web-vitals';

export function WebVitalsReporter() {
  useReportWebVitals((metric) => {
    if (process.env.NODE_ENV !== 'production') {
      console.log('[web-vitals]', metric.name, {
        value: metric.value,
        rating: metric.rating,
        delta: metric.delta,
        id: metric.id,
      });
    }
    // Production: no-op. Future: post to /api/vitals or analytics.
  });

  return null;
}

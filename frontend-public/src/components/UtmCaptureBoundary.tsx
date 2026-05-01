'use client';

import { useEffect } from 'react';
import { captureUtmFromUrl } from '@/lib/attribution/utm';

/**
 * Phase 2.3: capture UTM attribution at root layout mount, before any
 * client-side navigation can strip query params from window.location.
 *
 * Runs once per page load (not per route transition). The
 * captureUtmFromUrl function is idempotent: if the URL has UTM params
 * it persists them to sessionStorage; if the URL is clean it returns
 * previously-stored UTM (sessionStorage survives client-nav within the
 * same tab).
 *
 * Pure mount-time effect; renders children unchanged.
 */
export function UtmCaptureBoundary({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    captureUtmFromUrl();
  }, []);

  return <>{children}</>;
}

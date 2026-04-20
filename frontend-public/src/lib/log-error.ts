/**
 * Centralized error logger (Stage 4 Task 10b).
 *
 * Single hook point for future error telemetry wiring. Today this is
 * a thin wrapper over `console.error`; tomorrow it can call
 * Sentry.captureException, PostHog.capture, or similar without
 * touching every call site.
 *
 * Usage:
 *   import { logError } from '@/lib/log-error';
 *   try { ... } catch (err) { logError(err, { source: 'gallery.loadMore' }); }
 *
 * Context object is optional but recommended — attach anything that
 * would help identify the failure mode post-mortem.
 *
 * This module is intentionally 1 function + no dependencies. If a
 * real provider is added later, wire it here and nowhere else.
 */

export function logError(
  error: unknown,
  context?: Record<string, unknown>,
): void {
  // Keep console.error so developers see errors locally and so that
  // next.config.ts's compiler.removeConsole policy (which keeps
  // 'error') preserves this channel in production bundles.
  console.error('[error]', error, context);

  // Future: wire telemetry provider here. Keep this single function
  // as the only place such wiring touches.
}

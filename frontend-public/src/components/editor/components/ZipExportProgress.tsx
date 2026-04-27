'use client';
import React from 'react';
import { useTranslations } from 'next-intl';
import type { ZipExportPhase } from '../export/zipExport';

interface ZipExportProgressProps {
  phase: ZipExportPhase | null;
}

/**
 * Phase 2.1 PR#3 — Per-preset progress indicator for ZIP export.
 *
 * Per recon Q-2.1-5 / approval A: numeric counter "Rendering N/total..."
 * No preset-name labels (avoids 14+ i18n keys for preset display names).
 *
 * Renders inline (caller decides placement; typically replaces TopBar
 * Export button label during operation).
 */
export function ZipExportProgress({ phase }: ZipExportProgressProps) {
  const t = useTranslations('editor.export_zip.progress');

  if (!phase) return null;

  if (phase.phase === 'rendering') {
    return (
      <span aria-live="polite">
        {t('rendering', { current: phase.current, total: phase.total })}
      </span>
    );
  }

  if (phase.phase === 'packing') {
    return <span aria-live="polite">{t('packing')}</span>;
  }

  return null;
}

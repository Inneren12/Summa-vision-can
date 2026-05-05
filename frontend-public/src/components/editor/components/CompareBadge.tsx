/**
 * Phase 3.1d Slice 1b — CompareBadge component.
 *
 * Source of truth: docs/recon/phase-3-1d-slice-1b-recon.md §D.1, §D.2
 *
 * Text glyph + label badge. No icon library dependency (DEBT-074 closed:
 * text glyphs sufficient for v1). Inline styles match TopBar conventions.
 */

'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import type { CompareBadgeSeverity } from '@/lib/types/compare';
import { TK } from '../config/tokens';

const GLYPHS: Record<CompareBadgeSeverity, string> = {
  fresh: '✓', // ✓
  stale: '⚠', // ⚠
  missing: '×', // ×
  unknown: '?',
  partial: '◐', // ◐
};

const TONES: Record<
  CompareBadgeSeverity | 'not_compared',
  { background: string; color: string }
> = {
  fresh: { background: 'rgba(13,148,136,0.20)', color: TK.c.pos },
  stale: { background: TK.c.accM, color: TK.c.acc },
  missing: { background: 'rgba(225,29,72,0.18)', color: TK.c.err },
  partial: { background: TK.c.accM, color: TK.c.acc },
  unknown: { background: TK.c.bgAct, color: TK.c.txtM },
  not_compared: { background: TK.c.bgAct, color: TK.c.txtM },
};

export interface CompareBadgeProps {
  severity: CompareBadgeSeverity | 'not_compared';
  comparedAt?: string;
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffSec = Math.max(0, Math.round((now - then) / 1000));
  if (diffSec < 60) return `${diffSec}s`;
  if (diffSec < 3600) return `${Math.round(diffSec / 60)}m`;
  if (diffSec < 86400) return `${Math.round(diffSec / 3600)}h`;
  return `${Math.round(diffSec / 86400)}d`;
}

export function CompareBadge({ severity, comparedAt }: CompareBadgeProps) {
  const t = useTranslations('publication.compare');

  const labelKey =
    severity === 'not_compared' ? 'badge.not_compared' : `badge.${severity}`;
  const label = t(labelKey);
  const glyph = severity === 'not_compared' ? '?' : GLYPHS[severity];

  const tone = TONES[severity];

  const timestamp = comparedAt
    ? t('timestamp.compared_relative', { time: formatRelativeTime(comparedAt) })
    : null;

  return (
    <span
      data-testid="compare-badge"
      data-severity={severity}
      role="status"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 5px',
        fontFamily: TK.font.data,
        fontSize: '8px',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.4px',
        background: tone.background,
        color: tone.color,
        borderRadius: '2px',
        whiteSpace: 'nowrap',
      }}
    >
      <span aria-hidden="true">{glyph}</span>
      <span
        style={{
          position: 'absolute',
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: 'hidden',
          clip: 'rect(0,0,0,0)',
          whiteSpace: 'nowrap',
          border: 0,
        }}
      >
        {label}
      </span>
      <span aria-hidden="true">{label}</span>
      {timestamp && (
        <span aria-hidden="true" style={{ color: TK.c.txtM, fontWeight: 400 }}>
          {timestamp}
        </span>
      )}
    </span>
  );
}

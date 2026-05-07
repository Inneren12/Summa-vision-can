/**
 * Phase 3.1d Slice 1b — CompareBadge component.
 *
 * Source of truth: docs/recon/phase-3-1d-slice-1b-recon.md §D.1, §D.2
 *
 * Text glyph + label badge. No icon library dependency (DEBT-074 closed:
 * text glyphs sufficient for v1). Inline styles match TopBar conventions.
 *
 * Phase 3.1d Slice 5 (PR-08): optional `reasons` prop. When non-empty
 * the badge becomes hoverable/focusable and a sibling tooltip
 * (role="tooltip", linked via aria-describedby) lists the deduped union
 * of stale reasons. Visibility is component-local React state driven
 * by mouseenter/leave + focus/blur — no CSS-framework dependency.
 */

'use client';

import React, { useId, useState } from 'react';
import { useTranslations } from 'next-intl';
import type { CompareBadgeSeverity, StaleReason } from '@/lib/types/compare';
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
  /**
   * Phase 3.1d Slice 5 (PR-08): when non-empty, the badge wrapper
   * becomes hoverable/focusable and reveals a tooltip listing each
   * reason (i18n keys under `publication.compare.reasons.*`). When
   * empty/undefined, no tooltip is rendered and the wrapper is not
   * tab-stoppable.
   */
  reasons?: ReadonlyArray<StaleReason>;
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

export function CompareBadge({ severity, comparedAt, reasons }: CompareBadgeProps) {
  const t = useTranslations('publication.compare');
  const [isHovered, setIsHovered] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const tooltipId = useId();

  const labelKey =
    severity === 'not_compared' ? 'badge.not_compared' : `badge.${severity}`;
  const label = t(labelKey);
  const glyph = severity === 'not_compared' ? '?' : GLYPHS[severity];

  const tone = TONES[severity];

  const timestamp = comparedAt
    ? t('timestamp.compared_relative', { time: formatRelativeTime(comparedAt) })
    : null;

  const hasReasons = Boolean(reasons && reasons.length > 0);
  const tooltipVisible = hasReasons && (isHovered || isFocused);

  return (
    <span
      data-testid="compare-badge-wrapper"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      tabIndex={hasReasons ? 0 : -1}
      aria-describedby={tooltipVisible ? tooltipId : undefined}
      style={{ position: 'relative', display: 'inline-flex' }}
    >
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
      {tooltipVisible && reasons && (
        <ReasonsTooltip
          reasons={reasons}
          severityLabel={label}
          id={tooltipId}
        />
      )}
    </span>
  );
}

interface ReasonsTooltipProps {
  reasons: ReadonlyArray<StaleReason>;
  severityLabel: string;
  id: string;
}

function ReasonsTooltip({ reasons, severityLabel, id }: ReasonsTooltipProps) {
  const tReasons = useTranslations('publication.compare.reasons');
  const tTooltip = useTranslations('publication.compare.tooltip');
  return (
    <span
      role="tooltip"
      id={id}
      data-testid="compare-reasons-tooltip"
      style={{
        position: 'absolute',
        top: '100%',
        right: 0,
        marginTop: 4,
        padding: '6px 8px',
        background: TK.c.bgSurf,
        color: TK.c.txtP,
        fontFamily: TK.font.data,
        fontSize: 9,
        borderRadius: 3,
        border: `1px solid ${TK.c.brd}`,
        boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
        zIndex: 100,
        maxWidth: 240,
        whiteSpace: 'normal',
      }}
    >
      <span style={{ fontWeight: 600, display: 'block', marginBottom: 2 }}>
        {tTooltip('title', { severity: severityLabel })}
      </span>
      <ul style={{ margin: '4px 0 0', paddingLeft: 14, listStyle: 'disc' }}>
        {reasons.map((r) => (
          <li key={r}>{tReasons(r)}</li>
        ))}
      </ul>
    </span>
  );
}

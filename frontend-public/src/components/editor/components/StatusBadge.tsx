'use client';

import React from 'react';
import type { WorkflowState } from '../types';
import { TK } from '../config/tokens';

export interface StatusBadgeProps {
  workflow: WorkflowState;
  size?: 'compact' | 'regular';
}

interface BadgeStyle {
  background: string;
  color: string;
}

const STYLES: Record<WorkflowState, BadgeStyle> = {
  draft:     { background: 'rgba(92,99,112,0.20)',   color: TK.c.txtS },
  in_review: { background: TK.c.accM,                color: TK.c.acc },
  approved:  { background: 'rgba(13,148,136,0.20)',  color: TK.c.pos },
  exported:  { background: 'rgba(13,148,136,0.40)',  color: TK.c.pos },
  published: { background: 'rgba(251,191,36,0.40)',  color: TK.c.txtP },
};

const LABELS: Record<WorkflowState, string> = {
  draft:     'DRAFT',
  in_review: 'IN REVIEW',
  approved:  'APPROVED',
  exported:  'EXPORTED',
  published: 'PUBLISHED',
};

export function StatusBadge({ workflow, size = 'compact' }: StatusBadgeProps) {
  const tone = STYLES[workflow];
  const isCompact = size === 'compact';
  return (
    <span
      data-testid="status-badge"
      data-workflow={workflow}
      style={{
        display: 'inline-block',
        padding: isCompact ? '2px 5px' : '4px 10px',
        fontFamily: TK.font.data,
        fontSize: isCompact ? '8px' : '11px',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.4px',
        background: tone.background,
        color: tone.color,
        borderRadius: isCompact ? '2px' : '3px',
        whiteSpace: 'nowrap',
      }}
    >
      {LABELS[workflow]}
    </span>
  );
}

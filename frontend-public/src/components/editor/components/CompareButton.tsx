/**
 * Phase 3.1d Slice 1b — CompareButton component.
 *
 * Source of truth: docs/recon/phase-3-1d-slice-1b-recon.md §A.1.1
 */

'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import type { CompareState } from '../hooks/compareReducer';
import { TK } from '../config/tokens';

export interface CompareButtonProps {
  state: CompareState;
  onClick: () => void;
  disabled?: boolean;
}

export function CompareButton({
  state,
  onClick,
  disabled = false,
}: CompareButtonProps) {
  const t = useTranslations('publication.compare');
  const isLoading = state.kind === 'loading';
  const label = isLoading ? t('button.comparing') : t('button.compare');
  const isDisabled = disabled || isLoading;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isDisabled}
      aria-label={label}
      data-testid="compare-button"
      style={{
        padding: '3px 6px',
        fontSize: '8px',
        fontFamily: TK.font.data,
        background: TK.c.bgSurf,
        color: isDisabled ? TK.c.txtM : TK.c.txtS,
        border: `1px solid ${TK.c.brd}`,
        borderRadius: '2px',
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        opacity: isDisabled ? 0.6 : 1,
      }}
    >
      {label}
    </button>
  );
}

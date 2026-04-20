'use client';

import React from 'react';
import { TK } from '../config/tokens';
import type { SaveStatus } from '../types';

interface Props {
  dirty: boolean;
  saveStatus: SaveStatus;
}

// TopBar save-state glyph (Stage 4 Task 2). Replaces the single dirty dot
// that Task 0 shipped. Resolution order:
//   saveStatus='error'                → red dot,    aria "Save failed"
//   saveStatus='saving'               → amber pulse, aria "Saving"
//   dirty && saveStatus='pending'     → amber dot,   aria "Unsaved changes"
//   dirty && saveStatus='idle'        → amber dot,   aria "Unsaved changes"
//   !dirty && saveStatus='idle'       → null         (fully saved)
export function SaveStatusIndicator({ dirty, saveStatus }: Props) {
  if (saveStatus === 'error') {
    return (
      <span
        aria-label="Save failed"
        title="Save failed"
        data-testid="save-status-indicator"
        data-status="error"
        style={{ fontSize: '7px', color: TK.c.err, fontFamily: TK.font.data }}
      >
        {'\u25CF'}
      </span>
    );
  }

  if (saveStatus === 'saving') {
    return (
      <span
        aria-label="Saving"
        title="Saving\u2026"
        data-testid="save-status-indicator"
        data-status="saving"
        style={{
          fontSize: '7px',
          color: TK.c.acc,
          fontFamily: TK.font.data,
          animation: 'summa-save-pulse 1s ease-in-out infinite',
        }}
      >
        {'\u25CF'}
      </span>
    );
  }

  if (dirty) {
    return (
      <span
        aria-label="Unsaved changes"
        title="Unsaved changes"
        data-testid="save-status-indicator"
        data-status={saveStatus === 'pending' ? 'pending' : 'unsaved'}
        style={{ fontSize: '7px', color: TK.c.acc, fontFamily: TK.font.data }}
      >
        {'\u25CF'}
      </span>
    );
  }

  return null;
}

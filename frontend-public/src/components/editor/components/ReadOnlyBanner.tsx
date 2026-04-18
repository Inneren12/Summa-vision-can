'use client';

import React from 'react';
import type { EditorAction, WorkflowState } from '../types';
import { TK } from '../config/tokens';
import { availableTransitions, isReadOnlyWorkflow } from '../store/workflow';

export interface ReadOnlyBannerProps {
  workflow: WorkflowState;
  dispatch: React.Dispatch<EditorAction>;
}

const STATE_LABEL: Record<WorkflowState, string> = {
  draft: 'in draft',
  in_review: 'in review',
  approved: 'approved',
  exported: 'exported',
  published: 'published',
};

export function ReadOnlyBanner({ workflow, dispatch }: ReadOnlyBannerProps) {
  if (!isReadOnlyWorkflow(workflow)) return null;
  const canReturnToDraft = (availableTransitions(workflow) as readonly WorkflowState[]).includes('draft');
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="read-only-banner"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '8px 12px',
        background: `${TK.c.acc}14`,
        borderBottom: `1px solid ${TK.c.brd}`,
        color: TK.c.txtP,
        fontFamily: TK.font.body,
        fontSize: '12px',
        flexShrink: 0,
      }}
    >
      <span style={{ flex: 1 }}>
        This document is {STATE_LABEL[workflow]} and cannot be edited.
      </span>
      {canReturnToDraft && (
        <button
          type="button"
          onClick={() => dispatch({ type: 'RETURN_TO_DRAFT' })}
          style={{
            padding: '4px 10px',
            fontFamily: TK.font.data,
            fontSize: '9px',
            textTransform: 'uppercase',
            letterSpacing: '0.4px',
            background: TK.c.bgSurf,
            color: TK.c.txtP,
            border: `1px solid ${TK.c.brd}`,
            borderRadius: '3px',
            cursor: 'pointer',
          }}
        >
          Return to draft
        </button>
      )}
    </div>
  );
}

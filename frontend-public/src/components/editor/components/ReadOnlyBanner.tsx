'use client';

import React from 'react';
import type { EditorAction, EditorState, WorkflowState } from '../types';
import { TK } from '../config/tokens';
import { isReadOnlyWorkflow } from '../store/workflow';
import type { NoteRequestConfig } from './noteRequest';

export interface ReadOnlyBannerProps {
  state: EditorState;
  dispatch: React.Dispatch<EditorAction>;
  /**
   * Request the editor's shared NoteModal. Owned by `index.tsx`. Any
   * note-bearing transition (RETURN_TO_DRAFT) flows through this callback
   * so the audit trail is identical regardless of which surface initiated
   * the transition. Direct dispatches are reserved for transitions that
   * produce a fresh document (DUPLICATE_AS_DRAFT) and carry no note.
   */
  onRequestNote: (config: NoteRequestConfig) => void;
}

const STATE_LABEL: Record<WorkflowState, string> = {
  draft: 'in draft',
  in_review: 'in review',
  approved: 'approved',
  exported: 'exported',
  published: 'published',
};

export function ReadOnlyBanner({ state, dispatch, onRequestNote }: ReadOnlyBannerProps) {
  const workflow = state.doc.review.workflow;
  if (!isReadOnlyWorkflow(workflow)) return null;

  const message = `This document is ${STATE_LABEL[workflow]} and cannot be edited.`;

  const handleReturnToDraft = () => {
    onRequestNote({
      title: 'Return to draft',
      label: 'Reason (optional)',
      placeholder: 'Why is this document being returned to draft?',
      required: false,
      submitLabel: 'Return to draft',
      onSubmit: (note: string) =>
        dispatch({ type: 'RETURN_TO_DRAFT', note: note || undefined }),
    });
  };

  const handleDuplicate = () => {
    dispatch({ type: 'DUPLICATE_AS_DRAFT' });
  };

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="read-only-banner"
      data-workflow={workflow}
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
      <span style={{ flex: 1 }}>{message}</span>
      <div style={{ display: 'flex', gap: '8px' }}>
        {workflow === 'approved' && (
          <button
            type="button"
            data-testid="banner-return-to-draft"
            onClick={handleReturnToDraft}
            style={buttonStyle('secondary')}
          >
            Return to draft
          </button>
        )}
        {workflow === 'exported' && (
          <>
            <button
              type="button"
              data-testid="banner-duplicate"
              onClick={handleDuplicate}
              style={buttonStyle('primary')}
            >
              Duplicate as draft
            </button>
            <button
              type="button"
              data-testid="banner-return-to-draft"
              onClick={handleReturnToDraft}
              style={buttonStyle('secondary')}
            >
              Return to draft
            </button>
          </>
        )}
        {workflow === 'published' && (
          <button
            type="button"
            data-testid="banner-duplicate"
            onClick={handleDuplicate}
            style={buttonStyle('primary')}
          >
            Duplicate as draft
          </button>
        )}
      </div>
    </div>
  );
}

function buttonStyle(variant: 'primary' | 'secondary'): React.CSSProperties {
  const primary = variant === 'primary';
  return {
    padding: '4px 10px',
    fontFamily: TK.font.data,
    fontSize: '9px',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
    fontWeight: primary ? 700 : 500,
    background: primary ? TK.c.acc : TK.c.bgSurf,
    color: primary ? '#0B0D11' : TK.c.txtP,
    border: primary ? 'none' : `1px solid ${TK.c.brd}`,
    borderRadius: '3px',
    cursor: 'pointer',
  };
}

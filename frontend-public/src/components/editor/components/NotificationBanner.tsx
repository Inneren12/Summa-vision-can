'use client';

import React, { useEffect, useState } from 'react';
import type { EditorState, EditorAction } from '../types';
import { TK } from '../config/tokens';

export interface NotificationBannerProps {
  state: EditorState;
  importError: string | null;
  importWarnings: string[];
  onClearImportError: () => void;
  onClearImportWarnings: () => void;
  // Dispatch wired through so the save-error Dismiss button can clear
  // `state.saveError` without a second piece of lifted state. Optional
  // for legacy call sites that never surface save errors.
  dispatch?: (action: EditorAction) => void;
}

const NOOP_DISPATCH: (action: EditorAction) => void = () => {};

const ACTION_LABELS: Record<string, string> = {
  UPDATE_PROP: 'Edit',
  UPDATE_DATA: 'Edit data',
  TOGGLE_VIS: 'Toggle visibility',
  CHANGE_PAGE: 'Change page',
  SWITCH_TPL: 'Switch template',
  IMPORT: 'Import',
  UNDO: 'Undo',
  REDO: 'Redo',
  ADD_COMMENT: 'Comment',
  REPLY_TO_COMMENT: 'Reply',
  EDIT_COMMENT: 'Edit comment',
  RESOLVE_COMMENT: 'Resolve',
  REOPEN_COMMENT: 'Reopen',
  DELETE_COMMENT: 'Delete comment',
  SUBMIT_FOR_REVIEW: 'Submit for review',
  APPROVE: 'Approve',
  REQUEST_CHANGES: 'Request changes',
  RETURN_TO_DRAFT: 'Return to draft',
  MARK_EXPORTED: 'Mark exported',
  MARK_PUBLISHED: 'Mark published',
  DUPLICATE_AS_DRAFT: 'Duplicate',
};

function actionLabel(type: string): string {
  return ACTION_LABELS[type] ?? type;
}

export function NotificationBanner({
  state,
  importError,
  importWarnings,
  onClearImportError,
  onClearImportWarnings,
  dispatch = NOOP_DISPATCH,
}: NotificationBannerProps) {
  const rejection = state._lastRejection;
  const [rejectionDismissed, setRejectionDismissed] = useState<boolean>(false);

  // Reset dismissal when a new rejection arrives.
  useEffect(() => {
    setRejectionDismissed(false);
  }, [rejection?.at]);

  // Resolution priority (B4):
  //   saveError > importError > _lastRejection > importWarnings.
  // saveError wins because an unsuccessful persistence is the most
  // actionable state — the user needs to see it before any secondary
  // import/validation noise.
  if (state.saveError) {
    return (
      <div
        role="alert"
        aria-live="polite"
        data-testid="notification-banner"
        data-kind="save-error"
        style={bannerStyle({ background: `${TK.c.err}14`, color: TK.c.err })}
      >
        <div style={tagStyle()}>{'Save failed'}</div>
        <div style={bodyStyle()}>
          <div>{state.saveError}</div>
        </div>
        <button
          type="button"
          onClick={() => dispatch({ type: 'DISMISS_SAVE_ERROR' })}
          aria-label="Dismiss save error"
          title="Dismiss save error"
          style={dismissStyle()}
        >
          {'\u2715'}
        </button>
      </div>
    );
  }

  if (importError) {
    return (
      <div
        role="alert"
        aria-live="polite"
        data-testid="notification-banner"
        data-kind="import-error"
        style={bannerStyle({ background: `${TK.c.err}14`, color: TK.c.err })}
      >
        <div style={tagStyle()}>{'Import error'}</div>
        <div style={bodyStyle()}>
          <div>{importError}</div>
        </div>
        <button
          type="button"
          onClick={onClearImportError}
          aria-label="Dismiss import error"
          title="Dismiss import error"
          style={dismissStyle()}
        >
          {'\u2715'}
        </button>
      </div>
    );
  }

  if (rejection && !rejectionDismissed) {
    return (
      <div
        role="status"
        aria-live="polite"
        data-testid="notification-banner"
        data-kind="rejection"
        style={bannerStyle({ background: `${TK.c.err}14`, color: TK.c.err })}
      >
        <div style={tagStyle()}>{'Action blocked'}</div>
        <div style={bodyStyle()}>
          <div>
            <strong style={{ fontFamily: TK.font.data, fontSize: '8px', textTransform: 'uppercase' }}>
              {actionLabel(rejection.type)}
            </strong>
            {': '}
            {rejection.reason}
          </div>
        </div>
        <button
          type="button"
          onClick={() => setRejectionDismissed(true)}
          aria-label="Dismiss rejection notice"
          title="Dismiss rejection notice"
          style={dismissStyle()}
        >
          {'\u2715'}
        </button>
      </div>
    );
  }

  if (importWarnings.length > 0) {
    return (
      <div
        role="status"
        aria-live="polite"
        data-testid="notification-banner"
        data-kind="import-warnings"
        style={bannerStyle({ background: `${TK.c.acc}14`, color: TK.c.txtP })}
      >
        <div style={tagStyle()}>{'Import warnings'}</div>
        <div style={bodyStyle()}>
          <ul style={{ margin: 0, paddingLeft: '16px' }}>
            {importWarnings.map((w, i) => (
              <li key={`${w}_${i}`}>{w}</li>
            ))}
          </ul>
        </div>
        <button
          type="button"
          onClick={onClearImportWarnings}
          aria-label="Dismiss import warnings"
          title="Dismiss import warnings"
          style={dismissStyle()}
        >
          {'\u2715'}
        </button>
      </div>
    );
  }

  return null;
}

function bannerStyle({
  background,
  color,
}: {
  background: string;
  color: string;
}): React.CSSProperties {
  return {
    borderBottom: `1px solid ${TK.c.brd}`,
    background,
    color,
    padding: '6px 12px',
    display: 'flex',
    gap: '8px',
    alignItems: 'flex-start',
    flexShrink: 0,
  };
}

function tagStyle(): React.CSSProperties {
  return {
    fontSize: '8px',
    fontFamily: TK.font.data,
    textTransform: 'uppercase',
    minWidth: '90px',
  };
}

function bodyStyle(): React.CSSProperties {
  return { fontSize: '9px', lineHeight: 1.4, flex: 1 };
}

function dismissStyle(): React.CSSProperties {
  return {
    background: 'none',
    border: 'none',
    color: TK.c.txtM,
    cursor: 'pointer',
    fontSize: '10px',
    padding: 0,
  };
}

'use client';

import React, { useEffect, useId, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { TK } from '../config/tokens';

export interface PreconditionFailedModalProps {
  open: boolean;
  serverEtag: string | null;
  onReload: () => void;
  onSaveAsNewDraft: () => void;
  onDismiss: () => void;
}

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

function focusables(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
}

/**
 * Two-button modal surfaced on PATCH 412 PRECONDITION_FAILED. Q4=(a):
 *   - Reload (default focus, safer): drops local edits, re-fetches publication.
 *   - Save as new draft: clones source, PATCHes the clone with local snapshot.
 *
 * Esc / backdrop dismissal is non-resolving but non-looping (Phase 1.3 polish):
 * the dismissed conflict freezes autosave (`saveStatus = 'conflict'`) until the
 * user makes a fresh edit. That edit re-arms autosave to 'pending' and a new
 * PATCH fires, re-triggering this modal if the conflict is still real. User-
 * initiated retry, not auto-loop.
 */
export function PreconditionFailedModal({
  open,
  serverEtag,
  onReload,
  onSaveAsNewDraft,
  onDismiss,
}: PreconditionFailedModalProps) {
  const t = useTranslations('errors.backend.precondition_failed');
  const headingId = useId();
  const bodyId = useId();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const reloadButtonRef = useRef<HTMLButtonElement | null>(null);
  const previousActiveRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousActiveRef.current =
      typeof document !== 'undefined' && document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    queueMicrotask(() => {
      reloadButtonRef.current?.focus();
    });
    return () => {
      const prev = previousActiveRef.current;
      if (
        prev &&
        typeof prev.focus === 'function' &&
        typeof document !== 'undefined' &&
        document.contains(prev)
      ) {
        prev.focus();
      }
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (typeof document === 'undefined') return;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (typeof document === 'undefined') return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onDismiss();
        return;
      }
      if (e.key === 'Tab' && dialogRef.current) {
        const items = focusables(dialogRef.current);
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        const active = document.activeElement as HTMLElement | null;
        if (e.shiftKey) {
          if (active === first || !dialogRef.current.contains(active)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (active === last || !dialogRef.current.contains(active)) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    document.addEventListener('keydown', handler);
    return () => {
      document.removeEventListener('keydown', handler);
    };
  }, [open, onDismiss]);

  if (!open) return null;

  return (
    <div
      onClick={onDismiss}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 50,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        aria-describedby={bodyId}
        {...(process.env.NODE_ENV !== 'production' && { 'data-server-etag': serverEtag ?? '' })}
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '520px',
          background: TK.c.bgSurf,
          border: `1px solid ${TK.c.brd}`,
          borderRadius: '4px',
          padding: '16px 18px',
          color: TK.c.txtP,
          boxShadow: '0 12px 48px rgba(0,0,0,0.6)',
        }}
      >
        <h2
          id={headingId}
          style={{
            margin: 0,
            marginBottom: '12px',
            fontFamily: TK.font.display,
            fontSize: '14px',
            fontWeight: 600,
            color: TK.c.txtP,
          }}
        >
          {t('title')}
        </h2>
        <p
          id={bodyId}
          style={{
            margin: 0,
            marginBottom: '16px',
            fontFamily: TK.font.body,
            fontSize: '12px',
            color: TK.c.txtS,
            lineHeight: 1.5,
          }}
        >
          {t('body')}
        </p>
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '8px',
          }}
        >
          <button
            type="button"
            onClick={onSaveAsNewDraft}
            style={{
              padding: '5px 12px',
              fontFamily: TK.font.data,
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.3px',
              background: 'transparent',
              color: TK.c.txtS,
              border: `1px solid ${TK.c.brd}`,
              borderRadius: '3px',
              cursor: 'pointer',
            }}
          >
            {t('button_save_as_draft')}
          </button>
          <button
            type="button"
            ref={reloadButtonRef}
            onClick={onReload}
            style={{
              padding: '5px 12px',
              fontFamily: TK.font.data,
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.3px',
              fontWeight: 700,
              background: TK.c.acc,
              color: '#0B0D11',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
            }}
          >
            {t('button_reload')}
          </button>
        </div>
      </div>
    </div>
  );
}

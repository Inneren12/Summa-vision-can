'use client';

import React, { useEffect, useRef, useId } from 'react';
import { useTranslations } from 'next-intl';
import { TK } from '../config/tokens';

export interface DeleteConfirmModalProps {
  isOpen: boolean;
  blockLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const FOCUSABLE_SELECTOR =
  '[role="button"]:not([disabled]), button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusables(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
}

export function DeleteConfirmModal({
  isOpen,
  blockLabel,
  onConfirm,
  onCancel,
}: DeleteConfirmModalProps) {
  const t = useTranslations('editor.delete_confirm');
  const headingId = useId();
  const bodyId = useId();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const previousActiveRef = useRef<HTMLElement | null>(null);
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    previousActiveRef.current =
      typeof document !== 'undefined' && document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    queueMicrotask(() => {
      confirmButtonRef.current?.focus();
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
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    if (typeof document === 'undefined') return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
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
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      onClick={onCancel}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 60,
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
        data-testid="delete-confirm-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '440px',
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
            marginBottom: '8px',
            fontFamily: TK.font.display,
            fontSize: '14px',
            fontWeight: 600,
            color: TK.c.txtP,
          }}
        >
          {t('title', { block: blockLabel })}
        </h2>
        <p
          id={bodyId}
          style={{
            margin: 0,
            marginBottom: '14px',
            fontFamily: TK.font.body,
            fontSize: '12px',
            color: TK.c.txtS,
          }}
        >
          {t('body')}
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button
            type="button"
            data-testid="delete-confirm-cancel"
            onClick={onCancel}
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
            {t('cancel')}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            data-testid="delete-confirm-confirm"
            onClick={onConfirm}
            style={{
              padding: '5px 12px',
              fontFamily: TK.font.data,
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.3px',
              fontWeight: 700,
              background: TK.c.err,
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
            }}
          >
            {t('confirm')}
          </button>
        </div>
      </div>
    </div>
  );
}

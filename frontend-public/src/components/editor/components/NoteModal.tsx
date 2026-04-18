'use client';

import React, { useEffect, useRef, useState, useId } from 'react';
import { TK } from '../config/tokens';

export interface NoteModalProps {
  isOpen: boolean;
  title: string;
  label: string;
  placeholder?: string;
  initialValue?: string;
  submitLabel?: string;
  cancelLabel?: string;
  required?: boolean;
  maxLength?: number;
  onSubmit: (text: string) => void;
  onCancel: () => void;
}

const FOCUSABLE_SELECTOR =
  'textarea, [role="button"]:not([disabled]), button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusables(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
}

export function NoteModal({
  isOpen,
  title,
  label,
  placeholder,
  initialValue = '',
  submitLabel = 'Submit',
  cancelLabel = 'Cancel',
  required = false,
  maxLength = 2000,
  onSubmit,
  onCancel,
}: NoteModalProps) {
  const headingId = useId();
  const labelId = useId();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const previousActiveRef = useRef<HTMLElement | null>(null);
  const [value, setValue] = useState<string>(initialValue);

  useEffect(() => {
    if (!isOpen) return;
    setValue(initialValue);
    previousActiveRef.current =
      typeof document !== 'undefined' && document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    queueMicrotask(() => {
      textareaRef.current?.focus();
      textareaRef.current?.select();
    });
    return () => {
      const prev = previousActiveRef.current;
      if (prev && typeof prev.focus === 'function') {
        prev.focus();
      }
    };
    // initialValue intentionally only seeds on open transition.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  if (!isOpen) return null;

  const trimmed = value.trim();
  const overLimit = value.length > maxLength;
  const emptyBlocked = required && trimmed.length === 0;
  const submitDisabled = overLimit || emptyBlocked;

  const handleSubmit = () => {
    if (submitDisabled) return;
    onSubmit(trimmed);
  };

  const handleBackdropClick = () => {
    onCancel();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
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
        if (active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  };

  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
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
        aria-describedby={labelId}
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
          {title}
        </h2>
        <label
          id={labelId}
          htmlFor={`${headingId}-textarea`}
          style={{
            display: 'block',
            marginBottom: '6px',
            fontFamily: TK.font.body,
            fontSize: '11px',
            color: TK.c.txtS,
          }}
        >
          {label}
        </label>
        <textarea
          id={`${headingId}-textarea`}
          ref={textareaRef}
          value={value}
          placeholder={placeholder}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleTextareaKeyDown}
          rows={6}
          style={{
            width: '100%',
            fontFamily: TK.font.body,
            fontSize: '13px',
            color: TK.c.txtP,
            background: TK.c.bgApp,
            border: `1px solid ${TK.c.brd}`,
            padding: '8px',
            borderRadius: '3px',
            resize: 'vertical',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        <div
          aria-live="polite"
          style={{
            marginTop: '4px',
            fontFamily: TK.font.data,
            fontSize: '10px',
            color: overLimit ? TK.c.err : TK.c.txtM,
            textAlign: 'right',
          }}
        >
          {value.length} / {maxLength}
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '8px',
            marginTop: '12px',
          }}
        >
          <button
            type="button"
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
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitDisabled}
            style={{
              padding: '5px 12px',
              fontFamily: TK.font.data,
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.3px',
              fontWeight: 700,
              background: submitDisabled ? TK.c.bgAct : TK.c.acc,
              color: submitDisabled ? TK.c.txtM : '#0B0D11',
              border: 'none',
              borderRadius: '3px',
              cursor: submitDisabled ? 'not-allowed' : 'pointer',
            }}
          >
            {submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

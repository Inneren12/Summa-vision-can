'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import type { CanonicalDocument } from '../types';
import { walkBoundBlocks, type WalkerResult } from '../utils/walker';

export interface PublishConfirmModalProps {
  isOpen: boolean;
  doc: CanonicalDocument;
  isPublishing: boolean;
  error: Error | null;
  onConfirm: (walkerResult: WalkerResult) => void;
  onCancel: () => void;
}

export function PublishConfirmModal({
  isOpen,
  doc,
  isPublishing,
  error,
  onConfirm,
  onCancel,
}: PublishConfirmModalProps) {
  const t = useTranslations('publication.publish.modal');
  const walkerResult = useMemo(() => walkBoundBlocks(doc), [doc]);

  if (!isOpen) return null;

  const skippedTotal = walkerResult.deferred.length + walkerResult.skipped.length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="publish-confirm-modal-title"
      data-testid="publish-confirm-modal"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: '#fff',
          maxWidth: '480px',
          width: '90vw',
          padding: '20px',
          borderRadius: '4px',
          maxHeight: '80vh',
          overflowY: 'auto',
        }}
      >
        <h2
          id="publish-confirm-modal-title"
          style={{ margin: '0 0 12px', fontSize: '14px' }}
        >
          {t('title')}
        </h2>

        <p style={{ fontSize: '12px', marginBottom: '12px' }}>
          {t('summary', {
            count: walkerResult.boundBlocks.length,
            skipped: skippedTotal,
          })}
        </p>

        {walkerResult.deferred.length > 0 && (
          <details
            data-testid="publish-modal-deferred"
            style={{ marginBottom: '8px' }}
            open
          >
            <summary style={{ fontSize: '11px', cursor: 'pointer' }}>
              {t('deferred_heading', { count: walkerResult.deferred.length })}
            </summary>
            <ul style={{ fontSize: '10px', marginTop: '4px', paddingLeft: '16px' }}>
              {walkerResult.deferred.map((d) => (
                <li key={d.block_id}>
                  <code>{d.block_id}</code> — {d.kind}
                </li>
              ))}
            </ul>
          </details>
        )}

        {walkerResult.skipped.length > 0 && (
          <details
            data-testid="publish-modal-skipped"
            style={{ marginBottom: '8px' }}
            open
          >
            <summary style={{ fontSize: '11px', cursor: 'pointer' }}>
              {t('skipped_heading', { count: walkerResult.skipped.length })}
            </summary>
            <ul style={{ fontSize: '10px', marginTop: '4px', paddingLeft: '16px' }}>
              {walkerResult.skipped.map((s) => (
                <li key={s.block_id}>
                  <code>{s.block_id}</code> — {s.reason}
                </li>
              ))}
            </ul>
          </details>
        )}

        {error && (
          <div
            role="alert"
            data-testid="publish-modal-error"
            style={{
              color: '#a44',
              fontSize: '11px',
              marginBottom: '8px',
              padding: '6px 8px',
              background: '#fee',
              borderRadius: '3px',
            }}
          >
            {error.message}
          </div>
        )}

        <div
          style={{
            display: 'flex',
            gap: '8px',
            justifyContent: 'flex-end',
            marginTop: '12px',
          }}
        >
          <button
            type="button"
            onClick={onCancel}
            disabled={isPublishing}
            data-testid="publish-modal-cancel"
            style={{ fontSize: '11px', padding: '4px 10px' }}
          >
            {t('cancel_button')}
          </button>
          <button
            type="button"
            onClick={() => onConfirm(walkerResult)}
            disabled={isPublishing}
            data-testid="publish-modal-confirm"
            style={{
              fontSize: '11px',
              padding: '4px 10px',
              background: '#28a',
              color: '#fff',
              border: 'none',
              borderRadius: '3px',
            }}
          >
            {isPublishing ? t('publishing') : t('confirm_button')}
          </button>
        </div>
      </div>
    </div>
  );
}

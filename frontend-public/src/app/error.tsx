'use client';

import { useEffect } from 'react';
import { logError } from '@/lib/log-error';

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logError(error, { source: 'route-error', digest: error.digest });
  }, [error]);

  return (
    <div
      style={{
        padding: '3rem 1.5rem',
        minHeight: '50vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div style={{ maxWidth: 480, textAlign: 'center' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>
          Something went wrong
        </h2>
        <p style={{ opacity: 0.75, marginBottom: '1.25rem' }}>
          Please try again. If the problem persists, check back shortly.
        </p>
        <button
          type="button"
          onClick={reset}
          style={{
            padding: '0.5rem 1rem',
            background: '#5EEAD4',
            color: '#0B0D11',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          Try again
        </button>
      </div>
    </div>
  );
}

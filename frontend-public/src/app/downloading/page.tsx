'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { getDownloadUrl } from '@/lib/api/client';

type PageState = 'ready' | 'loading' | 'success' | 'error' | 'no-token';

export default function DownloadingPage() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState<string | null>(null);
  const [pageState, setPageState] = useState<PageState>('ready');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // On mount: read token from URL, then clear it from browser history
  useEffect(() => {
    const urlToken = searchParams.get('token');

    if (!urlToken) {
      setPageState('no-token');
      return;
    }

    // Store token in React state only — NOT localStorage/sessionStorage
    setToken(urlToken);

    // Clear the token from the URL to prevent it from persisting in browser history (R1, R17)
    window.history.replaceState({}, '', '/downloading');
  }, [searchParams]);

  function handleDownloadClick() {
    if (!token) return;

    setPageState('loading');

    // Use window.location.assign for the download — NOT fetch() (R1)
    // The 307 redirect from the backend triggers the browser to download
    const downloadUrl = getDownloadUrl(token);
    window.location.assign(downloadUrl);

    // Show success state after a short delay
    // (the browser will follow the redirect automatically)
    setTimeout(() => {
      setPageState('success');
    }, 2000);
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="bg-surface rounded-2xl p-8 w-full max-w-md shadow-2xl border border-white/10 text-center">
        {/* Summa Vision branding */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-text-primary">
            Summa Vision
          </h1>
          <p className="text-xs text-text-secondary uppercase tracking-wider mt-1">
            Canadian Macroeconomic Data
          </p>
        </div>

        {pageState === 'no-token' && (
          <div className="space-y-4">
            <div className="text-4xl mb-4" aria-hidden="true">
              &#9888;
            </div>
            <p className="text-text-primary font-semibold" data-testid="error-message">
              Invalid download link
            </p>
            <p className="text-text-secondary text-sm">
              Please check your email for the correct link.
            </p>
          </div>
        )}

        {pageState === 'ready' && token && (
          <div className="space-y-6">
            <div className="text-4xl mb-4" aria-hidden="true">
              &#128229;
            </div>
            <p className="text-text-primary font-semibold text-lg">
              Your download is ready
            </p>
            <p className="text-text-secondary text-sm">
              Click the button below to verify your link and start the download.
            </p>
            <button
              onClick={handleDownloadClick}
              className="w-full py-3 px-6 rounded-lg bg-neon-green text-background font-bold text-center hover:opacity-90 transition-opacity"
              data-testid="download-btn"
            >
              Verify and Download
            </button>
          </div>
        )}

        {pageState === 'loading' && (
          <div className="space-y-4">
            <div
              className="w-8 h-8 border-2 border-neon-green border-t-transparent rounded-full animate-spin mx-auto"
              aria-label="Loading"
              data-testid="loading-spinner"
            />
            <p className="text-text-secondary text-sm">
              Verifying your download link...
            </p>
          </div>
        )}

        {pageState === 'success' && (
          <div className="space-y-4">
            <div className="text-4xl mb-4" aria-hidden="true">
              &#10003;
            </div>
            <p className="text-text-primary font-semibold">
              Your download should start automatically
            </p>
            <p className="text-text-secondary text-sm">
              If the download doesn&apos;t start, check your browser&apos;s download
              settings or try again.
            </p>
          </div>
        )}

        {pageState === 'error' && (
          <div className="space-y-4">
            <div className="text-4xl mb-4" aria-hidden="true">
              &#9888;
            </div>
            <p className="text-text-primary font-semibold" data-testid="error-message">
              {errorMessage || 'Something went wrong'}
            </p>
            <a
              href="/graphics"
              className="inline-block w-full py-3 px-6 rounded-lg bg-white/10 text-text-primary font-semibold text-center hover:bg-white/20 transition-colors"
            >
              Request New Link
            </a>
          </div>
        )}
      </div>
    </main>
  );
}

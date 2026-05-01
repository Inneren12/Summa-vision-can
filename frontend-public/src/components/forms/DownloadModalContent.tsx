'use client';

import { useCallback, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { captureLeadForDownload } from '@/lib/api/client';
import { getStoredUtm } from '@/lib/attribution/utm';
import { emailSchema, type EmailFormValues } from '@/lib/schemas';
import TurnstileWidget from '@/components/forms/TurnstileWidget';

interface DownloadModalContentProps {
  assetId: number;
  onClose: () => void;
}

type ModalState = 'idle' | 'submitting' | 'success' | 'error';

export function DownloadModalContent({ assetId, onClose }: DownloadModalContentProps) {
  const [modalState, setModalState] = useState<ModalState>('idle');
  const [serverError, setServerError] = useState<string | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState<string>('');
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const turnstileRef = useRef<{ reset: () => void } | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EmailFormValues>({
    resolver: zodResolver(emailSchema),
  });

  const handleTurnstileSuccess = useCallback((token: string) => {
    setTurnstileToken(token);
  }, []);

  const handleTurnstileError = useCallback(() => {
    setTurnstileToken(null);
  }, []);

  async function onSubmit(values: EmailFormValues) {
    if (!turnstileToken) {
      setServerError('Please complete the verification challenge.');
      setModalState('error');
      return;
    }

    setModalState('submitting');
    setServerError(null);
    try {
      // Phase 2.3: UTM was already captured at root layout mount via
      // UtmCaptureBoundary. Read from sessionStorage at submit time so
      // we still get attribution after the visitor navigates client-side
      // away from the original ``?utm_*`` landing URL.
      const utm = getStoredUtm();
      await captureLeadForDownload(values.email, assetId, turnstileToken, utm);
      setSubmittedEmail(values.email);
      setModalState('success');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong.';

      if (message.includes('CAPTCHA')) {
        setServerError('Verification failed. Please try again.');
        turnstileRef.current?.reset();
        setTurnstileToken(null);
      } else if (message.includes('Too many')) {
        setServerError('Too many requests. Please wait a moment.');
      } else if (message.includes('not found') || message.includes('not yet published')) {
        setServerError('This graphic is no longer available.');
      } else {
        setServerError(message);
      }
      setModalState('error');
    }
  }

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center bg-bg-app/80"
      role="dialog"
      aria-modal="true"
      aria-label="Download infographic"
    >
      <div className="bg-bg-surface rounded-public p-8 w-full max-w-md mx-4 shadow-elevated border border-border-default">
        <div className="flex justify-between items-start mb-6">
          <h2 className="text-text-primary text-xl font-bold">
            Get the High-Res Version
          </h2>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="text-text-secondary hover:text-text-primary transition-colors text-2xl leading-none"
          >
            &times;
          </button>
        </div>

        {modalState === 'success' ? (
          /* Success state — email sent */
          <div className="text-center space-y-4">
            <div className="text-4xl mb-2" aria-hidden="true">
              &#9993;
            </div>
            <p className="text-text-primary font-semibold">
              Check your email!
            </p>
            <p className="text-text-secondary text-sm">
              We&apos;ve sent a download link to{' '}
              <strong className="text-text-primary">{submittedEmail}</strong>.
            </p>
            <p className="text-text-secondary text-xs">
              The link expires in 48 hours. Check your spam folder if you
              don&apos;t see it.
            </p>
          </div>
        ) : (
          /* Form state */
          <form
            onSubmit={handleSubmit(onSubmit)}
            noValidate
            className="space-y-4"
          >
            <p className="text-text-secondary text-sm">
              Enter your email to receive the full-resolution graphic.
            </p>

            <div>
              <label
                htmlFor={`email-${assetId}`}
                className="block text-sm text-text-secondary mb-1"
              >
                Email address
              </label>
              <input
                id={`email-${assetId}`}
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                className={`w-full px-4 py-2 rounded-public bg-bg-app border text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent ${
                  errors.email
                    ? 'border-destructive'
                    : 'border-border-default'
                }`}
                {...register('email')}
              />
              {errors.email && (
                <p
                  className="mt-1 text-xs text-destructive"
                  role="alert"
                  data-testid="email-error"
                >
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Turnstile CAPTCHA widget */}
            <TurnstileWidget
              ref={turnstileRef}
              onSuccess={handleTurnstileSuccess}
              onError={handleTurnstileError}
            />

            {serverError && (
              <p
                className="text-xs text-destructive"
                role="alert"
                data-testid="server-error"
              >
                {serverError}
              </p>
            )}

            <button
              type="submit"
              disabled={modalState === 'submitting'}
              className="w-full py-2 px-4 rounded-button bg-btn-primary-bg text-btn-primary-text font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {modalState === 'submitting' ? 'Sending...' : 'Get Download Link'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

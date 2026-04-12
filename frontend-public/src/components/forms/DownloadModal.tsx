'use client';

import { useCallback, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { captureLeadForDownload } from '@/lib/api/client';
import { emailSchema, type EmailFormValues } from '@/lib/schemas';
import TurnstileWidget from '@/components/forms/TurnstileWidget';

interface DownloadModalProps {
  assetId: number;
}

type ModalState = 'idle' | 'submitting' | 'success' | 'error';

export default function DownloadModal({ assetId }: DownloadModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [modalState, setModalState] = useState<ModalState>('idle');
  const [serverError, setServerError] = useState<string | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState<string>('');
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const turnstileRef = useRef<{ reset: () => void } | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<EmailFormValues>({
    resolver: zodResolver(emailSchema),
  });

  function openModal() {
    setIsOpen(true);
    setModalState('idle');
    setServerError(null);
    setSubmittedEmail('');
    setTurnstileToken(null);
    reset();
  }

  function closeModal() {
    setIsOpen(false);
  }

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
      await captureLeadForDownload(values.email, assetId, turnstileToken);
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
    <>
      {/* Trigger button */}
      <button
        onClick={openModal}
        className="w-full py-2 px-4 rounded-lg bg-neon-green text-background font-semibold text-sm hover:opacity-90 transition-opacity"
        aria-label={`Download infographic ${assetId}`}
      >
        Download High-Res
      </button>

      {/* Modal overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          role="dialog"
          aria-modal="true"
          aria-label="Download infographic"
        >
          <div className="bg-surface rounded-2xl p-8 w-full max-w-md mx-4 shadow-2xl border border-white/10">
            <div className="flex justify-between items-start mb-6">
              <h2 className="text-text-primary text-xl font-bold">
                Get the High-Res Version
              </h2>
              <button
                onClick={closeModal}
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
                    className={`w-full px-4 py-2 rounded-lg bg-background border text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-neon-green ${
                      errors.email
                        ? 'border-error-red'
                        : 'border-white/10'
                    }`}
                    {...register('email')}
                  />
                  {errors.email && (
                    <p
                      className="mt-1 text-xs text-error-red"
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
                    className="text-xs text-error-red"
                    role="alert"
                    data-testid="server-error"
                  >
                    {serverError}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={modalState === 'submitting'}
                  className="w-full py-2 px-4 rounded-lg bg-neon-green text-background font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {modalState === 'submitting' ? 'Sending...' : 'Get Download Link'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}

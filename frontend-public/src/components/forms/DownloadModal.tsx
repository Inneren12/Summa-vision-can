'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { captureLeadForDownload } from '@/lib/api/client';
import { emailSchema, type EmailFormValues } from '@/lib/schemas';

interface DownloadModalProps {
  assetId: number;
}

type ModalState = 'idle' | 'submitting' | 'success' | 'error';

export default function DownloadModal({ assetId }: DownloadModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [modalState, setModalState] = useState<ModalState>('idle');
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

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
    setDownloadUrl(null);
    setServerError(null);
    reset();
  }

  function closeModal() {
    setIsOpen(false);
  }

  async function onSubmit(values: EmailFormValues) {
    setModalState('submitting');
    setServerError(null);
    try {
      const res = await captureLeadForDownload(values.email, assetId);
      setDownloadUrl(res.download_url);
      setModalState('success');
    } catch (err) {
      setServerError(
        err instanceof Error ? err.message : 'Something went wrong.',
      );
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
                ×
              </button>
            </div>

            {modalState === 'success' && downloadUrl ? (
              /* Success state — show Download Now button, never auto-open */
              <div className="text-center space-y-4">
                <p className="text-text-secondary text-sm">
                  Your download is ready. Click below to save the file.
                </p>
                <a
                  href={downloadUrl}
                  download
                  className="inline-block w-full py-3 px-6 rounded-lg bg-neon-green text-background font-bold text-center hover:opacity-90 transition-opacity"
                  data-testid="download-now-btn"
                >
                  Download Now
                </a>
                <p className="text-text-secondary text-xs">
                  Link expires in 15 minutes.
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

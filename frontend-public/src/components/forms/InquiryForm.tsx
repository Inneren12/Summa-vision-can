'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { isBlockedEmailDomain } from '@/lib/constants/free_domains';

const inquirySchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  email: z
    .string()
    .email('Invalid email address')
    .refine((email) => !isBlockedEmailDomain(email), {
      message: 'Please use your corporate email address',
    }),
  budget: z.string().min(1, 'Please select a budget range'),
  message: z
    .string()
    .min(10, 'Message must be at least 10 characters')
    .max(2000),
});

type InquiryFormValues = z.infer<typeof inquirySchema>;

type FormState = 'idle' | 'submitting' | 'success' | 'error';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const BUDGET_OPTIONS = [
  { value: '', label: 'Select a budget range' },
  { value: '$500–$1,000/month', label: '$500–$1,000/month' },
  { value: '$1,000–$5,000/month', label: '$1,000–$5,000/month' },
  { value: '$5,000+/month', label: '$5,000+/month' },
  { value: "Let's discuss", label: "Let's discuss" },
];

export default function InquiryForm() {
  const [formState, setFormState] = useState<FormState>('idle');
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<InquiryFormValues>({
    resolver: zodResolver(inquirySchema),
    defaultValues: {
      name: '',
      email: '',
      budget: '',
      message: '',
    },
  });

  async function onSubmit(values: InquiryFormValues) {
    setFormState('submitting');
    setServerError(null);

    try {
      const res = await fetch(
        `${API_URL}/api/v1/public/sponsorship/inquire`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(values),
        },
      );

      if (res.ok) {
        setFormState('success');
        return;
      }

      if (res.status === 422) {
        const data = await res.json().catch(() => null);
        setServerError(
          data?.detail ?? 'Invalid submission. Please check your input.',
        );
      } else if (res.status === 429) {
        setServerError(
          "You've recently submitted an inquiry. Please wait a few minutes before trying again.",
        );
      } else {
        setServerError('Something went wrong. Please try again.');
      }
      setFormState('error');
    } catch {
      setServerError('Network error. Please check your connection and try again.');
      setFormState('error');
    }
  }

  if (formState === 'success') {
    return (
      <div
        className="rounded-2xl border border-neon-green/30 bg-surface p-8 text-center"
        data-testid="success-state"
      >
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-neon-green/10">
          <svg
            className="h-8 w-8 text-neon-green"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h3 className="mb-2 text-xl font-bold text-text-primary">
          Thank you!
        </h3>
        <p className="text-text-secondary">
          We&apos;ll be in touch within 24 hours.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="space-y-6"
      data-testid="inquiry-form"
    >
      {/* Name */}
      <div>
        <label
          htmlFor="inquiry-name"
          className="mb-1 block text-sm font-medium text-text-secondary"
        >
          Name
        </label>
        <input
          id="inquiry-name"
          type="text"
          autoComplete="name"
          placeholder="Your full name"
          className={`w-full rounded-lg border bg-background px-4 py-3 text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-neon-green ${
            errors.name ? 'border-error-red' : 'border-white/10'
          }`}
          {...register('name')}
        />
        {errors.name && (
          <p
            className="mt-1 text-xs text-error-red"
            role="alert"
            data-testid="name-error"
          >
            {errors.name.message}
          </p>
        )}
      </div>

      {/* Email */}
      <div>
        <label
          htmlFor="inquiry-email"
          className="mb-1 block text-sm font-medium text-text-secondary"
        >
          Company Email
        </label>
        <input
          id="inquiry-email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          className={`w-full rounded-lg border bg-background px-4 py-3 text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-neon-green ${
            errors.email ? 'border-error-red' : 'border-white/10'
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

      {/* Budget */}
      <div>
        <label
          htmlFor="inquiry-budget"
          className="mb-1 block text-sm font-medium text-text-secondary"
        >
          Budget
        </label>
        <select
          id="inquiry-budget"
          className={`w-full appearance-none rounded-lg border bg-background px-4 py-3 text-text-primary focus:outline-none focus:ring-2 focus:ring-neon-green ${
            errors.budget ? 'border-error-red' : 'border-white/10'
          }`}
          {...register('budget')}
        >
          {BUDGET_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {errors.budget && (
          <p
            className="mt-1 text-xs text-error-red"
            role="alert"
            data-testid="budget-error"
          >
            {errors.budget.message}
          </p>
        )}
      </div>

      {/* Message */}
      <div>
        <label
          htmlFor="inquiry-message"
          className="mb-1 block text-sm font-medium text-text-secondary"
        >
          Message
        </label>
        <textarea
          id="inquiry-message"
          rows={4}
          placeholder="Tell us about your goals and how we can help..."
          className={`w-full resize-none rounded-lg border bg-background px-4 py-3 text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-neon-green ${
            errors.message ? 'border-error-red' : 'border-white/10'
          }`}
          {...register('message')}
        />
        {errors.message && (
          <p
            className="mt-1 text-xs text-error-red"
            role="alert"
            data-testid="message-error"
          >
            {errors.message.message}
          </p>
        )}
      </div>

      {/* Server error */}
      {serverError && (
        <p
          className="text-sm text-error-red"
          role="alert"
          data-testid="server-error"
        >
          {serverError}
        </p>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={formState === 'submitting'}
        className="w-full rounded-lg bg-neon-green px-6 py-3 font-semibold text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {formState === 'submitting' ? (
          <span className="inline-flex items-center gap-2">
            <svg
              className="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Sending...
          </span>
        ) : (
          'Send Inquiry'
        )}
      </button>
    </form>
  );
}

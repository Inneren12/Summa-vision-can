'use client';

export function TryAgainButton() {
  return (
    <button
      className="px-4 py-2 rounded-button bg-bg-surface border border-border-default text-text-primary text-sm hover:bg-bg-surface-hover transition-colors"
      onClick={() => window.location.reload()}
    >
      Try again
    </button>
  );
}

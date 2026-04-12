'use client';

export function TryAgainButton() {
  return (
    <button
      className="px-4 py-2 rounded-lg bg-surface border border-white/10 text-text-primary text-sm hover:bg-white/5 transition-colors"
      onClick={() => window.location.reload()}
    >
      Try again
    </button>
  );
}

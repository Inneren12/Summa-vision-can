'use client';

export default function EditorErrorPage({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
      <h2 className="text-xl">Failed to load editor</h2>
      <p className="text-sm text-text-secondary">{error.message}</p>
      <button
        onClick={reset}
        className="px-6 py-3 rounded-button bg-bg-surface border border-border-default hover:bg-bg-surface-hover"
      >
        Retry
      </button>
    </div>
  );
}

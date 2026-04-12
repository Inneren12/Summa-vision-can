'use client';

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
      <h2 className="text-xl text-text-primary">Something went wrong loading this graphic</h2>
      <button
        onClick={reset}
        className="px-6 py-3 rounded-lg bg-surface border border-white/10 text-text-primary font-semibold hover:bg-white/5 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}

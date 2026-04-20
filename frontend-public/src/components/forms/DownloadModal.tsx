'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';

// The modal body (react-hook-form, zod resolver, TurnstileWidget, overlay
// JSX) lives in a separate chunk that loads on first click. Homepage with
// 24 InfographicCards pays zero RHF/zod/Turnstile hydration cost until a
// user actually opens a modal.
const DownloadModalContent = dynamic(
  () =>
    import('./DownloadModalContent').then((m) => m.DownloadModalContent),
  { ssr: false },
);

interface DownloadModalProps {
  assetId: number;
}

export default function DownloadModal({ assetId }: DownloadModalProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="w-full py-2 px-4 rounded-button bg-btn-primary-bg text-btn-primary-text font-semibold text-sm hover:opacity-90 transition-opacity"
        aria-label={`Download infographic ${assetId}`}
      >
        Download High-Res
      </button>

      {isOpen && (
        <DownloadModalContent
          assetId={assetId}
          onClose={() => setIsOpen(false)}
        />
      )}
    </>
  );
}

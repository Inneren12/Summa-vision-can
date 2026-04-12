'use client';

import { useState } from 'react';
import { fetchPublishedGraphics } from '@/lib/api';
import type { PublicationResponse } from '@/lib/api';
import { InfographicCard } from './InfographicCard';

interface LoadMoreButtonProps {
  initialOffset: number;
  limit: number;
  total: number;
}

export function LoadMoreButton({ initialOffset, limit, total }: LoadMoreButtonProps) {
  const [offset, setOffset] = useState(initialOffset);
  const [items, setItems] = useState<PublicationResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(initialOffset < total);

  async function loadMore() {
    if (isLoading || !hasMore) return;
    setIsLoading(true);
    try {
      const data = await fetchPublishedGraphics(limit, offset);
      setItems((prev) => [...prev, ...data.items]);
      setOffset(offset + limit);
      if (offset + limit >= data.total) {
        setHasMore(false);
      }
    } catch (err) {
      console.error('Failed to load more graphics', err);
    } finally {
      setIsLoading(false);
    }
  }

  if (!hasMore && items.length === 0) return null;

  return (
    <>
      {items.map((pub) => (
        <InfographicCard key={pub.id} pub={pub} />
      ))}

      {hasMore && (
        <div className="col-span-full flex justify-center mt-8">
          <button
            onClick={loadMore}
            disabled={isLoading}
            className="px-6 py-3 rounded-lg bg-surface border border-white/10 text-text-primary font-semibold hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </>
  );
}

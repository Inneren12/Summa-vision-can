import { fetchPublishedGraphics } from '@/lib/api/server';
import type { PaginatedResponse } from '@/lib/api/server';
import { InfographicCard } from './InfographicCard';
import { LoadMoreButton } from './LoadMoreButton';
import { TryAgainButton } from './TryAgainButton';

export default async function InfographicFeed() {
  let response: PaginatedResponse | null = null;
  const limit = 24;

  try {
    response = await fetchPublishedGraphics(limit, 0);
  } catch {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <p className="text-text-secondary text-center">
          Could not load graphics. Please try again later.
        </p>
        <TryAgainButton />
      </div>
    );
  }

  if (!response || response.items.length === 0) {
    return (
      <p className="text-text-secondary text-center py-12">
        New infographics coming soon. Check back later.
      </p>
    );
  }

  const publications = response.items;
  // Make sure we have the limit from the response (defaulting to requested limit)
  const actualLimit = response.limit || limit;
  const total = response.total || 0;
  const initialOffset = actualLimit;

  return (
    <section
      aria-label="Published infographics"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      {publications.map((pub, index) => (
        <InfographicCard
          key={pub.id}
          pub={pub}
          priority={index < 4} // Set priority=true for the first 4 images
        />
      ))}

      {initialOffset < total && (
        <LoadMoreButton
          initialOffset={initialOffset}
          limit={actualLimit}
          total={total}
        />
      )}
    </section>
  );
}

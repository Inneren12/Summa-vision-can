import Link from 'next/link';
import Image from 'next/image';
import DownloadModal from '@/components/forms/DownloadModal';
import type { PublicationResponse } from '@/lib/types/publication';

export function InfographicCard({ pub, priority = false }: { pub: PublicationResponse; priority?: boolean }) {
  const date = new Date(pub.created_at);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHrs / 24);

  let timeStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  if (diffHrs < 24) {
    timeStr = diffHrs === 1 ? '1 hour ago' : `${Math.max(1, diffHrs)} hours ago`;
  } else if (diffDays < 7) {
    timeStr = diffDays === 1 ? '1 day ago' : `${diffDays} days ago`;
  }

  return (
    <article className="bg-card-bg rounded-public overflow-hidden shadow-card flex flex-col">
      <Link href={`/graphics/${pub.id}`} className="relative aspect-video bg-bg-app/30 block hover:opacity-90 transition-opacity">
        {pub.cdn_url ? (
          <Image
            src={pub.cdn_url}
            alt={pub.headline}
            fill
            priority={priority}
            className="object-cover"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-text-secondary text-sm">
            No image available
          </div>
        )}
      </Link>
      <div className="p-5 flex flex-col gap-3 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-bold font-data px-2 py-1 rounded ${
              (pub.virality_score ?? 0) > 0.8
                ? 'text-data-positive bg-data-positive/10'
                : (pub.virality_score ?? 0) >= 0.7
                ? 'text-data-warning bg-data-warning/10'
                : 'text-destructive bg-destructive/10'
            }`}
          >
            {(pub.virality_score ?? 0).toFixed(1)}
          </span>
          <span className="text-xs text-text-secondary font-data uppercase tracking-wider flex-1">
            {pub.chart_type}
          </span>
          <span className="text-xs text-text-secondary font-data">
            {timeStr}
          </span>
        </div>
        <Link href={`/graphics/${pub.id}`} className="flex-1 hover:underline">
          <h2 className="text-text-primary font-display font-semibold text-sm leading-snug">
            {pub.headline}
          </h2>
        </Link>
        {/* DownloadModal is a Client Component — receives assetId as prop */}
        <DownloadModal assetId={pub.id} />
      </div>
    </article>
  );
}

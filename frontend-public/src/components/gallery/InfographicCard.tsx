import Link from 'next/link';
import Image from 'next/image';
import DownloadModal from '@/components/forms/DownloadModal';
import type { PublicationResponse } from '@/lib/api';

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
    <article className="bg-surface rounded-xl overflow-hidden border border-white/5 flex flex-col">
      <Link href={`/graphics/${pub.id}`} className="relative aspect-video bg-black/30 block hover:opacity-90 transition-opacity">
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
            className="text-xs font-bold px-2 py-1 rounded"
            style={{
              color:
                pub.virality_score > 0.8
                  ? '#00FF94'
                  : pub.virality_score >= 0.7
                  ? '#FFB700'
                  : '#FF006E',
              backgroundColor:
                pub.virality_score > 0.8
                  ? 'rgba(0,255,148,0.1)'
                  : pub.virality_score >= 0.7
                  ? 'rgba(255,183,0,0.1)'
                  : 'rgba(255,0,110,0.1)',
            }}
          >
            {pub.virality_score.toFixed(1)}
          </span>
          <span className="text-xs text-text-secondary uppercase tracking-wider flex-1">
            {pub.chart_type}
          </span>
          <span className="text-xs text-text-secondary">
            {timeStr}
          </span>
        </div>
        <Link href={`/graphics/${pub.id}`} className="flex-1 hover:underline">
          <h2 className="text-text-primary font-semibold text-sm leading-snug">
            {pub.headline}
          </h2>
        </Link>
        {/* DownloadModal is a Client Component — receives assetId as prop */}
        <DownloadModal assetId={pub.id} />
      </div>
    </article>
  );
}

import { fetchPublishedGraphics, type Publication } from '@/lib/api';
import DownloadModal from '@/components/forms/DownloadModal';
import Image from 'next/image';

function InfographicCard({ pub }: { pub: Publication }) {
  return (
    <article className="bg-surface rounded-xl overflow-hidden border border-white/5 flex flex-col">
      {pub.preview_url && (
        <div className="relative aspect-video bg-black/30">
          <Image
            src={pub.preview_url}
            alt={pub.headline}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        </div>
      )}
      <div className="p-5 flex flex-col gap-3 flex-1">
        <div className="flex items-center gap-2">
          <span
            className="text-xs font-bold px-2 py-1 rounded"
            style={{
              color:
                pub.virality_score > 8
                  ? '#00FF94'
                  : pub.virality_score >= 7
                  ? '#FFB700'
                  : '#FF006E',
              backgroundColor:
                pub.virality_score > 8
                  ? 'rgba(0,255,148,0.1)'
                  : pub.virality_score >= 7
                  ? 'rgba(255,183,0,0.1)'
                  : 'rgba(255,0,110,0.1)',
            }}
          >
            {pub.virality_score.toFixed(1)}
          </span>
          <span className="text-xs text-text-secondary uppercase tracking-wider">
            {pub.chart_type}
          </span>
        </div>
        <h2 className="text-text-primary font-semibold text-sm leading-snug flex-1">
          {pub.headline}
        </h2>
        {/* DownloadModal is a Client Component — receives assetId as prop */}
        <DownloadModal assetId={pub.id} />
      </div>
    </article>
  );
}

export default async function InfographicFeed() {
  let publications: Publication[] = [];

  try {
    publications = await fetchPublishedGraphics();
  } catch {
    return (
      <p className="text-text-secondary text-center py-12">
        Could not load graphics. Please try again later.
      </p>
    );
  }

  if (publications.length === 0) {
    return (
      <p className="text-text-secondary text-center py-12">
        No graphics published yet. Check back soon.
      </p>
    );
  }

  return (
    <section
      aria-label="Published infographics"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      {publications.map((pub) => (
        <InfographicCard key={pub.id} pub={pub} />
      ))}
    </section>
  );
}

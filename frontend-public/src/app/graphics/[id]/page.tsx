import { Metadata } from 'next';
import Image from 'next/image';
import { notFound } from 'next/navigation';
import { fetchGraphic } from '@/lib/api/server';
import DownloadModal from '@/components/forms/DownloadModal';

interface Props {
  // In Next.js 15+ async route segments, params is a Promise
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const graphic = await fetchGraphic(id);
    if (!graphic) throw new Error('Not found');
    return {
      title: `${graphic.headline} | Summa Vision`,
      description: `Canadian macro-economic data visualization: ${graphic.headline}`,
      openGraph: {
        title: graphic.headline,
        description: `Canadian macro-economic data visualization: ${graphic.headline}`,
        images: graphic.cdn_url ? [
          {
            url: graphic.cdn_url,
            width: 1200,
            height: 630,
            alt: graphic.headline,
          },
        ] : [],
        type: 'article',
      },
      twitter: {
        card: 'summary_large_image',
        title: graphic.headline,
        images: graphic.cdn_url ? [graphic.cdn_url] : [],
      },
    };
  } catch {
    return {
      title: 'Graphic Not Found | Summa Vision',
      description: 'The requested graphic could not be found.',
    };
  }
}

export default async function GraphicPage({ params }: Props) {
  const { id } = await params;
  let graphic;
  try {
    graphic = await fetchGraphic(id);
  } catch {
    notFound();
    return null; // Return null so TS knows we exit here during tests
  }

  if (!graphic) return null;

  const timeStr = new Date(graphic.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <main className="min-h-screen px-4 py-12 max-w-4xl mx-auto">
      <article className="bg-surface rounded-2xl overflow-hidden border border-white/5 flex flex-col shadow-xl">
        <header className="p-8 border-b border-white/5">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs font-bold px-2 py-1 rounded bg-white/10 text-text-primary">
              Version {graphic.version}
            </span>
            <span className="text-xs text-text-secondary uppercase tracking-wider">
              {graphic.chart_type}
            </span>
            <span className="text-xs text-text-secondary">
              {timeStr}
            </span>
          </div>
          <h1 className="text-3xl font-bold text-text-primary leading-tight mb-6">
            {graphic.headline}
          </h1>
          <div className="max-w-md">
            <DownloadModal assetId={graphic.id} />
          </div>
        </header>

        {graphic.cdn_url ? (
          <div className="relative w-full h-auto bg-black/50 p-4 sm:p-8">
            <Image
              src={graphic.cdn_url}
              alt={graphic.headline}
              width={1200}
              height={630}
              priority
              className="w-full h-auto object-contain rounded-lg"
              sizes="(max-width: 1024px) 100vw, 1024px"
            />
          </div>
        ) : (
          <div className="flex h-96 items-center justify-center text-text-secondary">
            No image available
          </div>
        )}
      </article>
    </main>
  );
}

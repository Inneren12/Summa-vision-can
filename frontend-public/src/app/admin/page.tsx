import Link from 'next/link';
import { fetchAdminPublicationListServer } from '@/lib/api/admin-server';

export const dynamic = 'force-dynamic';

export default async function AdminIndexPage() {
  const publications = await fetchAdminPublicationListServer({ limit: 100 });

  if (publications.length === 0) {
    return (
      <div>
        <h1 className="text-2xl font-display font-semibold mb-4">Publications</h1>
        <p className="text-text-secondary">No publications yet.</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-display font-semibold mb-6">Publications</h1>
      <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {publications.map((p) => (
          <li key={p.id}>
            <Link
              href={`/admin/editor/${p.id}`}
              className="block p-4 rounded-button border border-border-default bg-bg-surface hover:bg-bg-surface-hover transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs uppercase tracking-wide text-text-secondary">
                  {p.status}
                </span>
                {p.virality_score != null && (
                  <span className="text-xs text-text-secondary">
                    V:{p.virality_score.toFixed(1)}
                  </span>
                )}
              </div>
              <h2 className="font-semibold line-clamp-2">{p.headline}</h2>
              {p.eyebrow && (
                <p className="text-sm text-text-secondary mt-1">{p.eyebrow}</p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

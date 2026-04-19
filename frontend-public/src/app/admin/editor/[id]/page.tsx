import { notFound } from 'next/navigation';
import { fetchAdminPublicationServer } from '@/lib/api/admin-server';
import {
  hydrateDoc,
  HydrationError,
} from '@/components/editor/utils/persistence';
import type { CanonicalDocument } from '@/components/editor/types';
import AdminEditorClient from './AdminEditorClient';

export const dynamic = 'force-dynamic';

interface Props {
  params: Promise<{ id: string }>;
}

export default async function AdminEditorPage({ params }: Props) {
  const { id } = await params;
  const publication = await fetchAdminPublicationServer(id);
  if (!publication) {
    notFound();
  }

  let initialDoc: CanonicalDocument;
  try {
    initialDoc = hydrateDoc(publication);
  } catch (err) {
    if (err instanceof HydrationError) {
      // Server-side log; user-facing surface is error.tsx via re-throw.
      console.error(
        `[admin/editor] Hydration failed for publication ${err.publicationId}: ${err.message}`,
      );
    }
    throw err;
  }

  return <AdminEditorClient publicationId={id} initialDoc={initialDoc} />;
}

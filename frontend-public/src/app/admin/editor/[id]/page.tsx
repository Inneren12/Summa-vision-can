import { notFound } from 'next/navigation';
import { fetchAdminPublicationServer } from '@/lib/api/admin-server';
import { hydrateDoc } from '@/components/editor/utils/persistence';
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

  const initialDoc = hydrateDoc(publication);

  return <AdminEditorClient publicationId={id} initialDoc={initialDoc} />;
}

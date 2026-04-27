'use client';

import InfographicEditor from '@/components/editor';
import type { CanonicalDocument } from '@/components/editor/types';

interface Props {
  publicationId: string;
  initialDoc: CanonicalDocument;
  initialEtag: string | null;
}

export default function AdminEditorClient({
  publicationId,
  initialDoc,
  initialEtag,
}: Props) {
  return (
    <InfographicEditor
      publicationId={publicationId}
      initialDoc={initialDoc}
      initialEtag={initialEtag}
    />
  );
}

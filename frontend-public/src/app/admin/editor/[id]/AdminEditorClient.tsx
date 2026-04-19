'use client';

import InfographicEditor from '@/components/editor';
import type { CanonicalDocument } from '@/components/editor/types';

interface Props {
  publicationId: string;
  initialDoc: CanonicalDocument;
}

export default function AdminEditorClient({ publicationId, initialDoc }: Props) {
  return (
    <InfographicEditor
      publicationId={publicationId}
      initialDoc={initialDoc}
    />
  );
}

'use client';

/**
 * Phase 3.1d Slice 4a — usePublishAction.
 *
 * Orchestrates the combined publish transition:
 *   button → initiate() → modal opens → confirm(walkerResult)
 *      → publishAdminPublication(id, { bound_blocks })
 *      → on success: onPublishSuccess() (caller dispatches MARK_PUBLISHED)
 *      → on 404: onNotFound() (caller surfaces "Publication not found — reload")
 *      → on other error: error state set, modal stays open
 *
 * Walker is computed inside the modal (memoized on doc). The hook only
 * forwards the walker result to the network call. Workflow state never
 * advances unless the network publish succeeds — so no rollback needed.
 */
import { useCallback, useState } from 'react';
import {
  publishAdminPublication,
  AdminPublicationNotFoundError,
  BackendApiError,
} from '@/lib/api/admin';
import type { WalkerResult } from '../utils/walker';

export interface UsePublishActionOptions {
  publicationId: string | null | undefined;
  /**
   * Phase 3.1d Slice 4b (Recon Delta 03): current ETag forwarded as If-Match
   * for optimistic concurrency on POST /publish. Caller drives this from
   * the editor's etagRef. Null/undefined → backend tolerates (DEBT-079).
   */
  etag?: string | null;
  /**
   * Receives the new ETag returned by the publish response so the caller can
   * update its etagRef before subsequent PATCHes. May be null when the
   * server does not emit an ETag header (defensive — current backend always
   * does).
   */
  onPublishSuccess: (newEtag: string | null) => void;
  onNotFound: () => void;
  /**
   * Phase 3.1d Slice 4b: 412 PRECONDITION_FAILED branch. Caller surfaces
   * PreconditionFailedModal with the publish-specific copy.
   */
  onPreconditionFailed?: (info: { serverEtag: string | null }) => void;
}

export interface UsePublishActionReturn {
  isModalOpen: boolean;
  isPublishing: boolean;
  error: Error | null;
  initiate: () => void;
  cancel: () => void;
  confirm: (walkerResult: WalkerResult) => Promise<void>;
}

export function usePublishAction({
  publicationId,
  etag,
  onPublishSuccess,
  onNotFound,
  onPreconditionFailed,
}: UsePublishActionOptions): UsePublishActionReturn {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const initiate = useCallback(() => {
    if (!publicationId) {
      console.warn(
        '[usePublishAction] no publicationId — cannot publish (template-only session?)',
      );
      return;
    }
    setError(null);
    setIsModalOpen(true);
  }, [publicationId]);

  const cancel = useCallback(() => {
    if (isPublishing) return;
    setIsModalOpen(false);
    setError(null);
  }, [isPublishing]);

  const confirm = useCallback(
    async (walkerResult: WalkerResult) => {
      if (!publicationId || isPublishing) return;
      setIsPublishing(true);
      setError(null);
      try {
        const result = await publishAdminPublication(
          publicationId,
          { bound_blocks: walkerResult.boundBlocks },
          { ifMatch: etag ?? null },
        );
        setIsModalOpen(false);
        onPublishSuccess(result.etag);
      } catch (err) {
        if (err instanceof AdminPublicationNotFoundError) {
          setIsModalOpen(false);
          onNotFound();
        } else if (
          err instanceof BackendApiError &&
          err.code === 'PRECONDITION_FAILED'
        ) {
          // Phase 3.1d Slice 4b: 412 surfaces the PreconditionFailedModal
          // (publish copy variant) via the caller's onPreconditionFailed.
          // Confirm modal closes; workflow is NOT advanced.
          setIsModalOpen(false);
          const serverEtagRaw = err.details?.server_etag;
          const serverEtag =
            typeof serverEtagRaw === 'string' ? serverEtagRaw : null;
          onPreconditionFailed?.({ serverEtag });
        } else {
          setError(err instanceof Error ? err : new Error(String(err)));
        }
      } finally {
        setIsPublishing(false);
      }
    },
    [
      publicationId,
      isPublishing,
      etag,
      onPublishSuccess,
      onNotFound,
      onPreconditionFailed,
    ],
  );

  return { isModalOpen, isPublishing, error, initiate, cancel, confirm };
}

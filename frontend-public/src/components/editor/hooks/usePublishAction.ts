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
} from '@/lib/api/admin';
import type { WalkerResult } from '../utils/walker';

export interface UsePublishActionOptions {
  publicationId: string | null | undefined;
  onPublishSuccess: () => void;
  onNotFound: () => void;
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
  onPublishSuccess,
  onNotFound,
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
        await publishAdminPublication(publicationId, {
          bound_blocks: walkerResult.boundBlocks,
        });
        onPublishSuccess();
        setIsModalOpen(false);
      } catch (err) {
        if (err instanceof AdminPublicationNotFoundError) {
          setIsModalOpen(false);
          onNotFound();
        } else {
          setError(err instanceof Error ? err : new Error(String(err)));
        }
      } finally {
        setIsPublishing(false);
      }
    },
    [publicationId, isPublishing, onPublishSuccess, onNotFound],
  );

  return { isModalOpen, isPublishing, error, initiate, cancel, confirm };
}

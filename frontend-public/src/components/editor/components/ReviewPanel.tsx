'use client';

import React, { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import type {
  Comment,
  EditorAction,
  EditorState,
  WorkflowAction,
  WorkflowState,
} from '../types';
import { TK } from '../config/tokens';
import {
  buildThreads,
  CommentThreadNode,
  isThreadResolved,
  threadUnresolvedCount,
  TOMBSTONE_AUTHOR,
  TOMBSTONE_TEXT,
  truncate,
} from '../store/comments';
import { availableTransitions } from '../store/workflow';
import { checkWorkflowPermission } from '../store/permissions';
import { resolveBlockLabel } from '../utils/block-label';
import { StatusBadge } from './StatusBadge';
import type { NoteRequestConfig } from './noteRequest';
import { usePublishAction } from '../hooks/usePublishAction';
import { PublishConfirmModal } from './PublishConfirmModal';

const ACTOR_YOU = 'you';
const HISTORY_COLLAPSED_LIMIT = 6;

type TransitionDescriptor =
  | { kind: 'direct'; action: WorkflowAction; label: string }
  | { kind: 'note'; actionType: 'REQUEST_CHANGES' | 'RETURN_TO_DRAFT'; label: string; modalTitle: string };

function describeTransition(
  from: WorkflowState,
  to: WorkflowState,
  doc: EditorState['doc'],
  tReview: (key: string, values?: Record<string, unknown>) => string,
): TransitionDescriptor | null {
  if (from === 'draft' && to === 'in_review') {
    return { kind: 'direct', action: { type: 'SUBMIT_FOR_REVIEW' }, label: tReview('transition.in_review') };
  }
  if (from === 'in_review' && to === 'approved') {
    return { kind: 'direct', action: { type: 'APPROVE' }, label: tReview('transition.approved') };
  }
  if (from === 'in_review' && to === 'draft') {
    return {
      kind: 'note',
      actionType: 'REQUEST_CHANGES',
      label: tReview('transition.draft'),
      modalTitle: tReview('request_changes.title'),
    };
  }
  if (from === 'approved' && to === 'draft') {
    return {
      kind: 'note',
      actionType: 'RETURN_TO_DRAFT',
      label: tReview('transition.draft'),
      modalTitle: tReview('return_to_draft.title'),
    };
  }
  if (from === 'approved' && to === 'exported') {
    const filename = `${doc.templateId}-${Date.now()}.png`;
    return { kind: 'direct', action: { type: 'MARK_EXPORTED', filename }, label: tReview('transition.exported') };
  }
  if (from === 'exported' && to === 'published') {
    return {
      kind: 'direct',
      action: { type: 'MARK_PUBLISHED', channel: 'manual' },
      label: tReview('transition.published'),
    };
  }
  return null;
}

function formatTimestamp(iso: string): string {
  // YYYY-MM-DD HH:mm
  if (!iso || typeof iso !== 'string') return iso;
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!m) return iso;
  return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}`;
}

function isCommentEvent(action: string): boolean {
  return action.startsWith('comment_');
}

export interface ReviewPanelProps {
  state: EditorState;
  dispatch: React.Dispatch<EditorAction>;
  /**
   * Request the editor's shared NoteModal. Owned by `index.tsx` so ReviewPanel
   * and ReadOnlyBanner route through the same audit path: a note-bearing
   * transition (or a comment mutation that wants free-text input) never
   * dispatches directly from the UI — it always flows through NoteModal →
   * onSubmit(note) → dispatch.
   */
  onRequestNote: (config: NoteRequestConfig) => void;
  /**
   * Phase 3.1d Slice 4a: required for the publish confirm modal flow.
   * MARK_PUBLISHED transitions intercept the descriptor, open the modal,
   * and on confirm POST `bound_blocks` to the publish endpoint via
   * `publishAdminPublication(publicationId, ...)`. Optional because the
   * template-only editor session passes no publicationId; in that case
   * the publish hook warns and the modal never opens.
   */
  publicationId?: string;
}

export function ReviewPanel({
  state,
  dispatch,
  onRequestNote,
  publicationId,
}: ReviewPanelProps) {
  const tReview = useTranslations('review');
  const tBlockType = useTranslations('block.type');
  const tPublication = useTranslations('publication');
  const [showResolved, setShowResolved] = useState<boolean>(false);
  const [historyExpanded, setHistoryExpanded] = useState<boolean>(false);

  const workflow = state.doc.review.workflow;
  const selId = state.selectedBlockId;

  const threads = useMemo(
    () => buildThreads(state.doc.review.comments),
    [state.doc.review.comments],
  );

  const visibleThreads = showResolved ? threads : threads.filter((t) => !isThreadResolved(t));

  const canCommentCheck = checkWorkflowPermission(workflow, { type: 'ADD_COMMENT' });
  const canCommentNow = canCommentCheck.allowed;
  const commentBlockedReason = canCommentCheck.reason;

  const openAddCommentModal = () => {
    if (!selId) return;
    const blockType = state.doc.blocks[selId]?.type;
    const blockLabel = resolveBlockLabel(blockType, tBlockType, tReview);
    onRequestNote({
      title: tReview('comment.add_on_block', { block: blockLabel }),
      label: tReview('comment.label'),
      required: true,
      submitLabel: tReview('comment.add_button'),
      placeholder: tReview('comment.placeholder'),
      onSubmit: (text) => {
        dispatch({ type: 'ADD_COMMENT', blockId: selId, text });
      },
    });
  };

  const openReplyModal = (parentId: string) => {
    onRequestNote({
      title: tReview('reply.to_comment'),
      label: tReview('reply.action'),
      required: true,
      submitLabel: tReview('reply.action'),
      placeholder: tReview('reply.placeholder'),
      onSubmit: (text) => {
        dispatch({ type: 'REPLY_TO_COMMENT', parentId, text });
      },
    });
  };

  const openEditModal = (comment: Comment) => {
    onRequestNote({
      title: tReview('comment.edit'),
      label: tReview('comment.label'),
      required: true,
      initialValue: comment.text,
      submitLabel: tReview('note.save'),
      onSubmit: (text) => {
        dispatch({ type: 'EDIT_COMMENT', commentId: comment.id, text });
      },
    });
  };

  const publishAction = usePublishAction({
    publicationId,
    onPublishSuccess: () => {
      dispatch({ type: 'MARK_PUBLISHED', channel: 'manual' });
    },
    onNotFound: () => {
      // Surface "Publication not found — reload the page" via the existing
      // saveError banner channel (matches editor.md NotificationBanner
      // priority `saveError > importError > _lastRejection > warnings`).
      // canAutoRetry: false — terminal, manual reload only.
      dispatch({
        type: 'SAVE_FAILED',
        error: tPublication('not_found.reload'),
        canAutoRetry: false,
      });
    },
  });

  const handleTransitionClick = (descriptor: TransitionDescriptor) => {
    if (descriptor.kind === 'direct') {
      // Phase 3.1d Slice 4a: combined-transition interception. MARK_PUBLISHED
      // does not dispatch directly from the button click; instead it opens
      // the publish confirm modal. The reducer dispatch happens inside
      // `onPublishSuccess` once the network publish succeeds.
      //
      // Phase 3.1d Slice 4a fix (Badge P2-2): template-only sessions have
      // no publicationId — there is no backend publication to send
      // bound_blocks to. Preserve pre-Slice-4a behavior: direct dispatch
      // advances the local workflow to "published" without a network
      // call. Operator sees the workflow transition; no snapshot capture
      // is attempted (and none is meaningful in a template-only session).
      if (descriptor.action.type === 'MARK_PUBLISHED') {
        if (publicationId) {
          publishAction.initiate();
        } else {
          dispatch(descriptor.action);
        }
        return;
      }
      dispatch(descriptor.action);
      return;
    }
    onRequestNote({
      title: descriptor.modalTitle,
      label: tReview('note.optional'),
      required: false,
      submitLabel: tReview('note.confirm'),
      placeholder: tReview('note.placeholder'),
      onSubmit: (text) => {
        const note = text.length > 0 ? text : undefined;
        if (descriptor.actionType === 'REQUEST_CHANGES') {
          dispatch({ type: 'REQUEST_CHANGES', note });
        } else {
          dispatch({ type: 'RETURN_TO_DRAFT', note });
        }
      },
    });
  };

  const transitions = (availableTransitions(workflow) as readonly WorkflowState[])
    .map((to) => describeTransition(workflow, to, state.doc, tReview))
    .filter((d): d is TransitionDescriptor => d !== null);

  const showDuplicate = workflow === 'exported' || workflow === 'published';
  const history = state.doc.review.history;
  const historyToShow = historyExpanded ? history : history.slice(-HISTORY_COLLAPSED_LIMIT);

  return (
    <div
      data-testid="review-panel"
      style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
    >
      {/* HEADER: workflow */}
      <div
        style={{
          padding: '10px',
          borderBottom: `1px solid ${TK.c.brd}`,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '8px',
          }}
        >
          <StatusBadge workflow={workflow} size="regular" />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {transitions.map((t) => {
            const actionType =
              t.kind === 'direct' ? t.action.type : t.actionType;
            const probe = checkWorkflowPermission(workflow, { type: actionType });
            const disabled = !probe.allowed;
            const showArrow = actionType !== 'DUPLICATE_AS_DRAFT';
            return (
              <button
                key={`${t.label}_${actionType}`}
                type="button"
                onClick={() => handleTransitionClick(t)}
                disabled={disabled}
                title={disabled ? probe.reason : t.label}
                data-testid={`transition-${actionType}`}
                style={transitionButtonStyle(disabled)}
              >
                {showArrow && <span aria-hidden="true">→ </span>}
                {t.label}
              </button>
            );
          })}
          {showDuplicate && (
            <button
              type="button"
              onClick={() => dispatch({ type: 'DUPLICATE_AS_DRAFT' })}
              data-testid="transition-DUPLICATE_AS_DRAFT"
              style={transitionButtonStyle(false)}
            >
              {tReview('transition.duplicate_as_draft')}
            </button>
          )}
          {transitions.length === 0 && !showDuplicate && (
            <span
              style={{
                fontFamily: TK.font.data,
                fontSize: '8px',
                color: TK.c.txtM,
                textTransform: 'uppercase',
              }}
            >
              {tReview('transitions.empty')}
            </span>
          )}
        </div>
      </div>

      {/* THREADS */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '4px',
          }}
        >
          <span
            style={{
              fontFamily: TK.font.data,
              fontSize: '8px',
              color: TK.c.txtS,
              textTransform: 'uppercase',
              letterSpacing: '0.4px',
            }}
          >
            {tReview('threads.title_count', { count: visibleThreads.length })}
          </span>
          <label
            style={{
              fontFamily: TK.font.data,
              fontSize: '8px',
              color: TK.c.txtM,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <input
              type="checkbox"
              checked={showResolved}
              onChange={(e) => setShowResolved(e.target.checked)}
              data-testid="show-resolved-toggle"
            />
            {tReview('threads.show_resolved')}
          </label>
        </div>
        {visibleThreads.length === 0 && (
          <div
            style={{
              fontSize: '10px',
              color: TK.c.txtM,
              textAlign: 'center',
              padding: '12px 0',
            }}
          >
            {tReview('threads.empty')}
          </div>
        )}
        {visibleThreads.map((t) => (
          <ThreadCard
            key={t.id}
            thread={t}
            doc={state.doc}
            workflow={workflow}
            dispatch={dispatch}
            onReply={openReplyModal}
            onEdit={openEditModal}
            tReview={tReview}
            tBlockType={tBlockType}
          />
        ))}

        {/* ADD COMMENT composer */}
        {selId && (
          <div
            style={{
              marginTop: '6px',
              padding: '8px',
              border: `1px dashed ${TK.c.brd}`,
              borderRadius: '3px',
            }}
          >
            <div
              style={{
                fontFamily: TK.font.data,
                fontSize: '8px',
                color: TK.c.txtM,
                textTransform: 'uppercase',
                marginBottom: '6px',
              }}
            >
              {tReview('comment.on_block', {
                block: resolveBlockLabel(state.doc.blocks[selId]?.type, tBlockType, tReview),
              })}
            </div>
            <button
              type="button"
              onClick={openAddCommentModal}
              disabled={!canCommentNow}
              title={canCommentNow ? tReview('comment.add') : commentBlockedReason}
              data-testid="add-comment-button"
              style={addCommentButtonStyle(!canCommentNow)}
            >
              {tReview('comment.add')}
            </button>
          </div>
        )}
      </div>

      {/* HISTORY */}
      <div
        style={{
          padding: '10px',
          borderTop: `1px solid ${TK.c.brd}`,
          maxHeight: '180px',
          overflowY: 'auto',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '6px',
          }}
        >
          <span
            style={{
              fontFamily: TK.font.data,
              fontSize: '8px',
              color: TK.c.txtS,
              textTransform: 'uppercase',
              letterSpacing: '0.4px',
            }}
          >
            {tReview('history.title_count', { count: history.length })}
          </span>
          {history.length > HISTORY_COLLAPSED_LIMIT && (
            <button
              type="button"
              onClick={() => setHistoryExpanded((v) => !v)}
              data-testid="history-toggle"
              style={{
                background: 'none',
                border: 'none',
                color: TK.c.acc,
                fontFamily: TK.font.data,
                fontSize: '8px',
                textTransform: 'uppercase',
                cursor: 'pointer',
              }}
            >
              {historyExpanded
                ? tReview('history.collapse')
                : tReview('history.show_all', { count: history.length })}
            </button>
          )}
        </div>
        {history.length === 0 && (
          <div
            style={{
              fontSize: '10px',
              color: TK.c.txtM,
              textAlign: 'center',
              padding: '6px 0',
            }}
          >
            {tReview('history.empty')}
          </div>
        )}
        <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
          {[...historyToShow].reverse().map((entry, idx) => {
            const muted = isCommentEvent(entry.action);
            return (
              <li
                key={`${entry.ts}_${idx}`}
                data-testid="history-entry"
                data-event-kind={muted ? 'comment' : 'workflow'}
                style={{
                  padding: '4px 0',
                  borderBottom: `1px solid ${TK.c.brd}`,
                  color: muted ? TK.c.txtS : TK.c.txtP,
                }}
              >
                <div
                  style={{
                    fontFamily: TK.font.data,
                    fontSize: '8px',
                    color: TK.c.txtM,
                    textTransform: 'uppercase',
                    letterSpacing: '0.4px',
                  }}
                >
                  {formatTimestamp(entry.ts)} · {entry.action} · {entry.author}
                </div>
                <div style={{ fontSize: '10px', lineHeight: 1.4 }}>
                  {truncate(entry.summary, 160)}
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <PublishConfirmModal
        isOpen={publishAction.isModalOpen}
        doc={state.doc}
        isPublishing={publishAction.isPublishing}
        error={publishAction.error}
        onConfirm={publishAction.confirm}
        onCancel={publishAction.cancel}
      />
    </div>
  );
}

interface ThreadCardProps {
  thread: CommentThreadNode;
  doc: EditorState['doc'];
  workflow: WorkflowState;
  dispatch: React.Dispatch<EditorAction>;
  onReply: (parentId: string) => void;
  onEdit: (comment: Comment) => void;
  tReview: (key: string, values?: Record<string, unknown>) => string;
  tBlockType: (key: string, values?: Record<string, unknown>) => string;
}

function ThreadCard({
  thread,
  doc,
  workflow,
  dispatch,
  onReply,
  onEdit,
  tReview,
  tBlockType,
}: ThreadCardProps) {
  const replyCheck = checkWorkflowPermission(workflow, { type: 'REPLY_TO_COMMENT' });
  const resolveCheck = checkWorkflowPermission(workflow, { type: 'RESOLVE_COMMENT' });
  const blockType = doc.blocks[thread.blockId]?.type;
  const unresolved = threadUnresolvedCount(thread);

  return (
    <div
      data-testid="thread-card"
      data-thread-id={thread.id}
      style={{
        background: TK.c.bgSurf,
        border: `1px solid ${TK.c.brd}`,
        borderRadius: '3px',
        padding: '8px',
      }}
    >
      <button
        type="button"
        onClick={() => dispatch({ type: 'SELECT', blockId: thread.blockId })}
        data-testid="thread-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          width: '100%',
          background: 'transparent',
          border: 'none',
          padding: 0,
          marginBottom: '6px',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span
          style={{
            fontFamily: TK.font.data,
            fontSize: '8px',
            color: TK.c.txtS,
            textTransform: 'uppercase',
          }}
        >
          {resolveBlockLabel(blockType, tBlockType, tReview)}
        </span>
        {unresolved > 0 && (
          <span
            data-testid="unresolved-pill"
            style={{
              padding: '1px 5px',
              background: TK.c.accM,
              color: TK.c.acc,
              fontFamily: TK.font.data,
              fontSize: '8px',
              borderRadius: '2px',
            }}
          >
            {unresolved}
          </span>
        )}
        <span
          style={{
            marginLeft: 'auto',
            fontFamily: TK.font.data,
            fontSize: '8px',
            color: TK.c.txtM,
          }}
        >
          {formatTimestamp(thread.createdAt)}
        </span>
      </button>

        <CommentBody
          comment={thread}
        workflow={workflow}
        resolveAllowed={resolveCheck.allowed}
        resolveReason={resolveCheck.reason}
          dispatch={dispatch}
          onEdit={onEdit}
          tReview={tReview}
        />

      {thread.replies.length > 0 && (
        <div
          style={{
            marginTop: '6px',
            paddingLeft: '16px',
            borderLeft: `2px solid ${TK.c.brd}`,
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {thread.replies.map((reply) => (
            <CommentBody
              key={reply.id}
              comment={reply}
              workflow={workflow}
              resolveAllowed={resolveCheck.allowed}
              resolveReason={resolveCheck.reason}
              dispatch={dispatch}
              onEdit={onEdit}
              tReview={tReview}
            />
          ))}
        </div>
      )}

      <div style={{ marginTop: '6px', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="button"
          onClick={() => onReply(thread.id)}
          disabled={!replyCheck.allowed}
          title={replyCheck.allowed ? tReview('reply.to_thread') : replyCheck.reason}
          data-testid="reply-button"
          style={smallButtonStyle(!replyCheck.allowed)}
        >
          {tReview('reply.action')}
        </button>
      </div>
    </div>
  );
}

interface CommentBodyProps {
  comment: Comment;
  workflow: WorkflowState;
  resolveAllowed: boolean;
  resolveReason?: string;
  dispatch: React.Dispatch<EditorAction>;
  onEdit: (comment: Comment) => void;
  tReview: (key: string, values?: Record<string, unknown>) => string;
}

function CommentBody({
  comment,
  workflow,
  resolveAllowed,
  resolveReason,
  dispatch,
  onEdit,
  tReview,
}: CommentBodyProps) {
  const isTombstone =
    comment.author === TOMBSTONE_AUTHOR && comment.text === TOMBSTONE_TEXT;
  const isOwn = comment.author === ACTOR_YOU;
  const editCheck = checkWorkflowPermission(workflow, { type: 'EDIT_COMMENT' });
  const deleteCheck = checkWorkflowPermission(workflow, { type: 'DELETE_COMMENT' });

  if (isTombstone) {
    return (
      <div
        data-testid="comment-body"
        data-tombstone="true"
        style={{
          fontFamily: TK.font.body,
          fontSize: '10px',
          color: TK.c.txtM,
          fontStyle: 'italic',
        }}
      >
        {tReview('comment.deleted')}
      </div>
    );
  }

  return (
    <div data-testid="comment-body" data-comment-id={comment.id}>
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: '6px',
          marginBottom: '2px',
        }}
      >
        <strong
          style={{
            fontFamily: TK.font.data,
            fontSize: '9px',
            color: TK.c.txtP,
          }}
        >
          {comment.author}
        </strong>
        <span
          style={{
            fontFamily: TK.font.data,
            fontSize: '8px',
            color: TK.c.txtM,
          }}
        >
          {formatTimestamp(comment.createdAt)}
          {comment.updatedAt ? tReview('comment.edited_suffix') : ''}
        </span>
        {comment.resolved && (
          <span
            style={{
              fontFamily: TK.font.data,
              fontSize: '8px',
              color: TK.c.pos,
              textTransform: 'uppercase',
            }}
          >
            {tReview('comment.resolved')}
          </span>
        )}
      </div>
      <div
        style={{
          fontFamily: TK.font.body,
          fontSize: '11px',
          color: TK.c.txtP,
          whiteSpace: 'pre-wrap',
          marginBottom: '4px',
        }}
      >
        {comment.text}
      </div>
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {comment.resolved ? (
          <button
            type="button"
            onClick={() => dispatch({ type: 'REOPEN_COMMENT', commentId: comment.id })}
            disabled={!resolveAllowed}
            title={resolveAllowed ? tReview('comment.reopen') : resolveReason}
            data-testid="reopen-button"
            style={smallButtonStyle(!resolveAllowed)}
          >
            {tReview('comment.reopen')}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => dispatch({ type: 'RESOLVE_COMMENT', commentId: comment.id })}
            disabled={!resolveAllowed}
            title={resolveAllowed ? tReview('comment.resolve') : resolveReason}
            data-testid="resolve-button"
            style={smallButtonStyle(!resolveAllowed)}
          >
            {tReview('comment.resolve')}
          </button>
        )}
        {isOwn && (
          <>
            <button
              type="button"
              onClick={() => onEdit(comment)}
              disabled={!editCheck.allowed}
              title={editCheck.allowed ? tReview('comment.edit_action') : editCheck.reason}
              data-testid="edit-button"
              style={smallButtonStyle(!editCheck.allowed)}
            >
              {tReview('comment.edit_action')}
            </button>
            <button
              type="button"
              onClick={() => dispatch({ type: 'DELETE_COMMENT', commentId: comment.id })}
              disabled={!deleteCheck.allowed}
              title={deleteCheck.allowed ? tReview('comment.delete') : deleteCheck.reason}
              data-testid="delete-button"
              style={smallButtonStyle(!deleteCheck.allowed)}
            >
              {tReview('comment.delete')}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function transitionButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '4px 8px',
    fontFamily: TK.font.data,
    fontSize: '9px',
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
    background: disabled ? TK.c.bgAct : TK.c.bgSurf,
    color: disabled ? TK.c.txtM : TK.c.txtP,
    border: `1px solid ${TK.c.brd}`,
    borderRadius: '3px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  };
}

function smallButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '2px 7px',
    fontFamily: TK.font.data,
    fontSize: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
    background: disabled ? TK.c.bgAct : 'transparent',
    color: disabled ? TK.c.txtM : TK.c.txtS,
    border: `1px solid ${TK.c.brd}`,
    borderRadius: '2px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  };
}

function addCommentButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '5px 10px',
    fontFamily: TK.font.data,
    fontSize: '9px',
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
    fontWeight: 700,
    background: disabled ? TK.c.bgAct : TK.c.acc,
    color: disabled ? TK.c.txtM : '#0B0D11',
    border: 'none',
    borderRadius: '3px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  };
}

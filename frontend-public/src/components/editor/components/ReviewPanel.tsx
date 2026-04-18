'use client';

import React, { useMemo, useState } from 'react';
import type {
  Comment,
  EditorAction,
  EditorState,
  WorkflowAction,
  WorkflowState,
} from '../types';
import { TK } from '../config/tokens';
import {
  blockDisplayLabel,
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
import { StatusBadge } from './StatusBadge';
import { NoteModal } from './NoteModal';

const ACTOR_YOU = 'you';
const HISTORY_COLLAPSED_LIMIT = 6;

const TRANSITION_LABELS: Record<WorkflowState, string> = {
  draft: 'Draft',
  in_review: 'In review',
  approved: 'Approved',
  exported: 'Exported',
  published: 'Published',
};

type TransitionDescriptor =
  | { kind: 'direct'; action: WorkflowAction; label: string }
  | { kind: 'note'; actionType: 'REQUEST_CHANGES' | 'RETURN_TO_DRAFT'; label: string; modalTitle: string };

function describeTransition(
  from: WorkflowState,
  to: WorkflowState,
  doc: EditorState['doc'],
): TransitionDescriptor | null {
  if (from === 'draft' && to === 'in_review') {
    return { kind: 'direct', action: { type: 'SUBMIT_FOR_REVIEW' }, label: '→ In review' };
  }
  if (from === 'in_review' && to === 'approved') {
    return { kind: 'direct', action: { type: 'APPROVE' }, label: '→ Approved' };
  }
  if (from === 'in_review' && to === 'draft') {
    return {
      kind: 'note',
      actionType: 'REQUEST_CHANGES',
      label: '→ Draft',
      modalTitle: 'Request changes',
    };
  }
  if (from === 'approved' && to === 'draft') {
    return {
      kind: 'note',
      actionType: 'RETURN_TO_DRAFT',
      label: '→ Draft',
      modalTitle: 'Return to draft',
    };
  }
  if (from === 'approved' && to === 'exported') {
    const filename = `${doc.templateId}-${Date.now()}.png`;
    return { kind: 'direct', action: { type: 'MARK_EXPORTED', filename }, label: '→ Exported' };
  }
  if (from === 'exported' && to === 'published') {
    return {
      kind: 'direct',
      action: { type: 'MARK_PUBLISHED', channel: 'manual' },
      label: '→ Published',
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

interface ModalRequest {
  title: string;
  label: string;
  required: boolean;
  initialValue?: string;
  placeholder?: string;
  submitLabel?: string;
  onSubmit: (text: string) => void;
}

export interface ReviewPanelProps {
  state: EditorState;
  dispatch: React.Dispatch<EditorAction>;
}

export function ReviewPanel({ state, dispatch }: ReviewPanelProps) {
  const [modal, setModal] = useState<ModalRequest | null>(null);
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
    const blockLabel = blockDisplayLabel(blockType);
    setModal({
      title: `Add comment on ${blockLabel}`,
      label: 'Comment',
      required: true,
      submitLabel: 'Add',
      placeholder: 'Type your comment...',
      onSubmit: (text) => {
        dispatch({ type: 'ADD_COMMENT', blockId: selId, text });
        setModal(null);
      },
    });
  };

  const openReplyModal = (parentId: string) => {
    setModal({
      title: 'Reply to comment',
      label: 'Reply',
      required: true,
      submitLabel: 'Reply',
      placeholder: 'Type your reply...',
      onSubmit: (text) => {
        dispatch({ type: 'REPLY_TO_COMMENT', parentId, text });
        setModal(null);
      },
    });
  };

  const openEditModal = (comment: Comment) => {
    setModal({
      title: 'Edit comment',
      label: 'Comment',
      required: true,
      initialValue: comment.text,
      submitLabel: 'Save',
      onSubmit: (text) => {
        dispatch({ type: 'EDIT_COMMENT', commentId: comment.id, text });
        setModal(null);
      },
    });
  };

  const handleTransitionClick = (descriptor: TransitionDescriptor) => {
    if (descriptor.kind === 'direct') {
      dispatch(descriptor.action);
      return;
    }
    setModal({
      title: descriptor.modalTitle,
      label: 'Note (optional)',
      required: false,
      submitLabel: 'Confirm',
      placeholder: 'Optional context for this transition...',
      onSubmit: (text) => {
        const note = text.length > 0 ? text : undefined;
        if (descriptor.actionType === 'REQUEST_CHANGES') {
          dispatch({ type: 'REQUEST_CHANGES', note });
        } else {
          dispatch({ type: 'RETURN_TO_DRAFT', note });
        }
        setModal(null);
      },
    });
  };

  const transitions = (availableTransitions(workflow) as readonly WorkflowState[])
    .map((to) => describeTransition(workflow, to, state.doc))
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
              Duplicate as draft
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
              No transitions available
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
            Threads ({visibleThreads.length})
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
            Show resolved
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
            No threads to show.
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
              On {blockDisplayLabel(state.doc.blocks[selId]?.type)}
            </div>
            <button
              type="button"
              onClick={openAddCommentModal}
              disabled={!canCommentNow}
              title={canCommentNow ? 'Add comment' : commentBlockedReason}
              data-testid="add-comment-button"
              style={addCommentButtonStyle(!canCommentNow)}
            >
              Add comment
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
            History ({history.length})
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
                ? 'Collapse'
                : `Show all ${history.length}`}
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
            No events yet.
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

      <NoteModal
        isOpen={modal !== null}
        title={modal?.title ?? ''}
        label={modal?.label ?? ''}
        placeholder={modal?.placeholder}
        initialValue={modal?.initialValue}
        submitLabel={modal?.submitLabel}
        required={modal?.required ?? false}
        onSubmit={(text) => modal?.onSubmit(text)}
        onCancel={() => setModal(null)}
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
}

function ThreadCard({
  thread,
  doc,
  workflow,
  dispatch,
  onReply,
  onEdit,
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
          {blockDisplayLabel(blockType)}
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
            />
          ))}
        </div>
      )}

      <div style={{ marginTop: '6px', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="button"
          onClick={() => onReply(thread.id)}
          disabled={!replyCheck.allowed}
          title={replyCheck.allowed ? 'Reply to thread' : replyCheck.reason}
          data-testid="reply-button"
          style={smallButtonStyle(!replyCheck.allowed)}
        >
          Reply
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
}

function CommentBody({
  comment,
  workflow,
  resolveAllowed,
  resolveReason,
  dispatch,
  onEdit,
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
        Comment deleted
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
          {comment.updatedAt ? ' (edited)' : ''}
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
            Resolved
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
            title={resolveAllowed ? 'Reopen' : resolveReason}
            data-testid="reopen-button"
            style={smallButtonStyle(!resolveAllowed)}
          >
            Reopen
          </button>
        ) : (
          <button
            type="button"
            onClick={() => dispatch({ type: 'RESOLVE_COMMENT', commentId: comment.id })}
            disabled={!resolveAllowed}
            title={resolveAllowed ? 'Resolve' : resolveReason}
            data-testid="resolve-button"
            style={smallButtonStyle(!resolveAllowed)}
          >
            Resolve
          </button>
        )}
        {isOwn && (
          <>
            <button
              type="button"
              onClick={() => onEdit(comment)}
              disabled={!editCheck.allowed}
              title={editCheck.allowed ? 'Edit' : editCheck.reason}
              data-testid="edit-button"
              style={smallButtonStyle(!editCheck.allowed)}
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => dispatch({ type: 'DELETE_COMMENT', commentId: comment.id })}
              disabled={!deleteCheck.allowed}
              title={deleteCheck.allowed ? 'Delete' : deleteCheck.reason}
              data-testid="delete-button"
              style={smallButtonStyle(!deleteCheck.allowed)}
            >
              Delete
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

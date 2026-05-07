'use client';

import React, { memo, useId, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import type {
  Block,
  BlockRegistryEntry,
  EditorAction,
  EditorMode,
  EditorState,
} from '../types';
import type { ContrastIssue } from '../validation/contrast';
import { TK } from '../config/tokens';
import {
  buildThreads,
  isThreadResolved,
  threadUnresolvedCount,
} from '../store/comments';
import { Inspector } from './Inspector';
import { ReviewPanel } from './ReviewPanel';
import type { NoteRequestConfig } from './noteRequest';

type RightRailTab = 'inspector' | 'review';
const TAB_ORDER: readonly RightRailTab[] = ['inspector', 'review'] as const;

export interface RightRailProps {
  state: EditorState;
  dispatch: React.Dispatch<EditorAction>;
  selB: Block | null;
  selR: BlockRegistryEntry | null;
  selId: string | null;
  mode: EditorMode;
  canEdit: (reg: BlockRegistryEntry, k: string) => boolean;
  onRequestNote: (config: NoteRequestConfig) => void;
  contrastIssues: ContrastIssue[];
  /** Phase 3.1d Slice 4a: forwarded to ReviewPanel for publish-vs-direct branching. */
  publicationId?: string;
  /**
   * Phase 3.1d Slice 5 (PR-08): publish flow lifted to editor root. RightRail
   * forwards the minimal surface to ReviewPanel — the active flag (for
   * disabling the transition button) and the initiate callback.
   */
  isPublishing?: boolean;
  onRequestPublish?: () => void;
}

function RightRailImpl({
  state,
  dispatch,
  selB,
  selR,
  selId,
  mode,
  canEdit,
  onRequestNote,
  contrastIssues,
  publicationId,
  isPublishing,
  onRequestPublish,
}: RightRailProps) {
  const tRightRail = useTranslations('right_rail');
  const [tab, setTab] = useState<RightRailTab>('inspector');
  const inspectorTabId = useId();
  const reviewTabId = useId();
  const inspectorPanelId = useId();
  const reviewPanelId = useId();
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([null, null]);

  const unresolvedTotal = useMemo(() => {
    const threads = buildThreads(state.doc.review.comments);
    let total = 0;
    for (const t of threads) {
      if (!isThreadResolved(t)) total += threadUnresolvedCount(t);
    }
    return total;
  }, [state.doc.review.comments]);

  const handleTabKey = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    const currentIdx = TAB_ORDER.indexOf(tab);
    let nextIdx = currentIdx;
    switch (e.key) {
      case 'ArrowRight':
        nextIdx = (currentIdx + 1) % TAB_ORDER.length;
        break;
      case 'ArrowLeft':
        nextIdx = (currentIdx - 1 + TAB_ORDER.length) % TAB_ORDER.length;
        break;
      case 'Home':
        nextIdx = 0;
        break;
      case 'End':
        nextIdx = TAB_ORDER.length - 1;
        break;
      default:
        return;
    }
    e.preventDefault();
    const nextTab = TAB_ORDER[nextIdx];
    setTab(nextTab);
    tabRefs.current[nextIdx]?.focus();
  };

  return (
    <aside
      data-testid="right-rail"
      style={{
        width: '280px',
        minWidth: '280px',
        borderLeft: `1px solid ${TK.c.brd}`,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        role="tablist"
        aria-label={tRightRail('aria_label')}
        style={{ display: 'flex', borderBottom: `1px solid ${TK.c.brd}` }}
      >
        <button
          type="button"
          id={inspectorTabId}
          role="tab"
          ref={(el) => { tabRefs.current[0] = el; }}
          aria-selected={tab === 'inspector'}
          aria-controls={inspectorPanelId}
          tabIndex={tab === 'inspector' ? 0 : -1}
          onClick={() => setTab('inspector')}
          onKeyDown={handleTabKey}
          style={tabButtonStyle(tab === 'inspector')}
        >
          {tRightRail('tab.inspector')}
        </button>
        <button
          type="button"
          id={reviewTabId}
          role="tab"
          ref={(el) => { tabRefs.current[1] = el; }}
          aria-selected={tab === 'review'}
          aria-controls={reviewPanelId}
          tabIndex={tab === 'review' ? 0 : -1}
          onClick={() => setTab('review')}
          onKeyDown={handleTabKey}
          style={tabButtonStyle(tab === 'review')}
        >
          {tRightRail('tab.review')}
          {unresolvedTotal > 0 && (
            <span
              data-testid="review-tab-pill"
              style={{
                marginLeft: '6px',
                padding: '2px 5px',
                background: TK.c.accM,
                color: TK.c.acc,
                borderRadius: '2px',
                fontFamily: TK.font.data,
                fontSize: '8px',
              }}
            >
              {unresolvedTotal}
            </span>
          )}
        </button>
      </div>
      <div
        id={inspectorPanelId}
        role="tabpanel"
        aria-labelledby={inspectorTabId}
        hidden={tab !== 'inspector'}
        style={{ flex: tab === 'inspector' ? 1 : 0, display: 'flex', minHeight: 0 }}
      >
        {tab === 'inspector' && (
          <Inspector
            selB={selB}
            selR={selR}
            selId={selId}
            mode={mode}
            canEdit={canEdit}
            dispatch={dispatch}
            contrastIssues={contrastIssues}
          />
        )}
      </div>
      <div
        id={reviewPanelId}
        role="tabpanel"
        aria-labelledby={reviewTabId}
        hidden={tab !== 'review'}
        style={{ flex: tab === 'review' ? 1 : 0, display: 'flex', minHeight: 0 }}
      >
        {tab === 'review' && (
          <ReviewPanel
            state={state}
            dispatch={dispatch}
            onRequestNote={onRequestNote}
            publicationId={publicationId}
            isPublishing={isPublishing}
            onRequestPublish={onRequestPublish}
          />
        )}
      </div>
    </aside>
  );
}

export const RightRail = memo(RightRailImpl);

function tabButtonStyle(active: boolean): React.CSSProperties {
  return {
    flex: 1,
    padding: '6px 8px',
    fontFamily: TK.font.data,
    fontSize: '9px',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
    background: active ? TK.c.bgAct : 'transparent',
    color: active ? TK.c.acc : TK.c.txtM,
    border: 'none',
    borderBottom: active
      ? `2px solid ${TK.c.acc}`
      : '2px solid transparent',
    cursor: 'pointer',
  };
}

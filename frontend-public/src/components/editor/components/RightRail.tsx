'use client';

import React, { useId, useMemo, useState } from 'react';
import type {
  Block,
  BlockRegistryEntry,
  EditorAction,
  EditorMode,
  EditorState,
} from '../types';
import { TK } from '../config/tokens';
import {
  buildThreads,
  isThreadResolved,
  threadUnresolvedCount,
} from '../store/comments';
import { Inspector } from './Inspector';
import { ReviewPanel } from './ReviewPanel';

type RightRailTab = 'inspector' | 'review';

export interface RightRailProps {
  state: EditorState;
  dispatch: React.Dispatch<EditorAction>;
  selB: Block | null;
  selR: BlockRegistryEntry | null;
  selId: string | null;
  mode: EditorMode;
  canEdit: (reg: BlockRegistryEntry, k: string) => boolean;
}

export function RightRail({
  state,
  dispatch,
  selB,
  selR,
  selId,
  mode,
  canEdit,
}: RightRailProps) {
  const [tab, setTab] = useState<RightRailTab>('inspector');
  const inspectorTabId = useId();
  const reviewTabId = useId();
  const inspectorPanelId = useId();
  const reviewPanelId = useId();

  const unresolvedTotal = useMemo(() => {
    const threads = buildThreads(state.doc.review.comments);
    let total = 0;
    for (const t of threads) {
      if (!isThreadResolved(t)) total += threadUnresolvedCount(t);
    }
    return total;
  }, [state.doc.review.comments]);

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
        aria-label="Right rail"
        style={{ display: 'flex', borderBottom: `1px solid ${TK.c.brd}` }}
      >
        <button
          type="button"
          id={inspectorTabId}
          role="tab"
          aria-selected={tab === 'inspector'}
          aria-controls={inspectorPanelId}
          onClick={() => setTab('inspector')}
          style={tabButtonStyle(tab === 'inspector')}
        >
          Inspector
        </button>
        <button
          type="button"
          id={reviewTabId}
          role="tab"
          aria-selected={tab === 'review'}
          aria-controls={reviewPanelId}
          onClick={() => setTab('review')}
          style={tabButtonStyle(tab === 'review')}
        >
          Review
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
          <ReviewPanel state={state} dispatch={dispatch} />
        )}
      </div>
    </aside>
  );
}

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

/**
 * Phase 3.1d Slice 5 (PR-08) — ReviewPanel publish-callback tests.
 *
 * Post-lift, ReviewPanel no longer owns `usePublishAction` or
 * `PublishConfirmModal` — both live in the editor root. ReviewPanel's
 * publish surface is now:
 *   - clicking the MARK_PUBLISHED transition fires `onRequestPublish`
 *     (when publicationId is present)
 *   - clicking the same transition without a publicationId falls back
 *     to a direct MARK_PUBLISHED dispatch (template-only session,
 *     pre-Slice-4a Badge P2-2 behavior)
 *   - the transition button is disabled while `isPublishing` is true
 *
 * Network behavior (etag forwarding, 404, 412, ordering) is covered by
 * `hooks/__tests__/usePublishAction.test.tsx` — the hook IS the publish
 * flow now, regardless of which surface (TopBar CTA or ReviewPanel
 * transition button) calls `initiate()`.
 */
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { ReviewPanel } from '../ReviewPanel';
import { initState, reducer } from '../../store/reducer';
import type { EditorAction, EditorState } from '../../types';

function makeExportedState(): EditorState {
  let state = initState();
  const path: EditorAction[] = [
    { type: 'SUBMIT_FOR_REVIEW' },
    { type: 'APPROVE' },
    { type: 'MARK_EXPORTED', filename: 'test.png' },
  ];
  for (const a of path) state = reducer(state, a);
  return state;
}

describe('ReviewPanel — MARK_PUBLISHED transition (Slice 5 lift)', () => {
  it('clicking publish transition with publicationId fires onRequestPublish', () => {
    const state = makeExportedState();
    const dispatch = jest.fn();
    const onRequestPublish = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        publicationId="p1"
        onRequestPublish={onRequestPublish}
      />,
    );

    fireEvent.click(screen.getByTestId('transition-MARK_PUBLISHED'));

    expect(onRequestPublish).toHaveBeenCalledTimes(1);
    // No direct MARK_PUBLISHED dispatch — flow goes through the lifted
    // confirm modal owned by editor root.
    expect(
      dispatch.mock.calls.find(
        (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
      ),
    ).toBeUndefined();
  });

  it('falls back to direct dispatch when publicationId is absent (template-only, Badge P2-2)', () => {
    const state = makeExportedState();
    const dispatch = jest.fn();
    const onRequestPublish = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        // publicationId intentionally omitted
        onRequestPublish={onRequestPublish}
      />,
    );

    fireEvent.click(screen.getByTestId('transition-MARK_PUBLISHED'));

    expect(onRequestPublish).not.toHaveBeenCalled();
    const markCalls = dispatch.mock.calls.filter(
      (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
    );
    expect(markCalls).toHaveLength(1);
    expect(markCalls[0][0]).toEqual({
      type: 'MARK_PUBLISHED',
      channel: 'manual',
    });
  });

  it('publicationId present + missing onRequestPublish does NOT dispatch MARK_PUBLISHED (P1-1 safety)', () => {
    // PR-08 R2 fix: silently advancing the workflow without a network
    // publish would leave snapshots uncaptured. Defensive surface is a
    // SAVE_FAILED toast naming the wiring bug.
    const state = makeExportedState();
    const dispatch = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        publicationId="p1"
        // onRequestPublish intentionally omitted — wiring-bug simulation
      />,
    );

    fireEvent.click(screen.getByTestId('transition-MARK_PUBLISHED'));

    const markCalls = dispatch.mock.calls.filter(
      (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
    );
    expect(markCalls).toHaveLength(0);

    const saveFailedCalls = dispatch.mock.calls.filter(
      (c) => (c[0] as EditorAction).type === 'SAVE_FAILED',
    );
    expect(saveFailedCalls).toHaveLength(1);
    // Error message comes from publish_flow_unavailable.reload key —
    // next-intl mock returns the dotted key as the resolved string.
    expect(
      (saveFailedCalls[0][0] as { error: string }).error,
    ).toContain('publish_flow_unavailable');
  });

  it('publish transition button is disabled while isPublishing=true', () => {
    const state = makeExportedState();
    render(
      <ReviewPanel
        state={state}
        dispatch={jest.fn()}
        onRequestNote={jest.fn()}
        publicationId="p1"
        onRequestPublish={jest.fn()}
        isPublishing
      />,
    );

    expect(screen.getByTestId('transition-MARK_PUBLISHED')).toBeDisabled();
  });

  it('publish transition button is NOT disabled when isPublishing=false', () => {
    const state = makeExportedState();
    render(
      <ReviewPanel
        state={state}
        dispatch={jest.fn()}
        onRequestNote={jest.fn()}
        publicationId="p1"
        onRequestPublish={jest.fn()}
        isPublishing={false}
      />,
    );

    expect(screen.getByTestId('transition-MARK_PUBLISHED')).not.toBeDisabled();
  });
});

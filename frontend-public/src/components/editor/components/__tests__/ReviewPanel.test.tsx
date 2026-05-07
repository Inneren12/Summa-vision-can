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

  it('falls back to direct dispatch when onRequestPublish is missing', () => {
    const state = makeExportedState();
    const dispatch = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        publicationId="p1"
        // onRequestPublish intentionally omitted — defensive fallback
      />,
    );

    fireEvent.click(screen.getByTestId('transition-MARK_PUBLISHED'));

    const markCalls = dispatch.mock.calls.filter(
      (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
    );
    expect(markCalls).toHaveLength(1);
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

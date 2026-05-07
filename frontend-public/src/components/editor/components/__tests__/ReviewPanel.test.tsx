/**
 * Phase 3.1d Slice 4a — ReviewPanel publish-modal interception tests.
 *
 * Verifies that clicking the workflow MARK_PUBLISHED transition does NOT
 * directly dispatch to the reducer; instead it opens the PublishConfirmModal,
 * and the reducer dispatch fires only after the network publish succeeds.
 */
import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { ReviewPanel } from '../ReviewPanel';
import { initState } from '../../store/reducer';
import { reducer } from '../../store/reducer';
import type { CanonicalDocument, EditorAction, EditorState } from '../../types';

jest.mock('@/lib/api/admin', () => {
  class AdminPublicationNotFoundError extends Error {
    constructor(id: string) {
      super(`Publication ${id} not found`);
      this.name = 'AdminPublicationNotFoundError';
    }
  }
  return {
    publishAdminPublication: jest.fn(),
    AdminPublicationNotFoundError,
  };
});

import {
  publishAdminPublication,
  AdminPublicationNotFoundError,
} from '@/lib/api/admin';

const publishMock = publishAdminPublication as jest.MockedFunction<
  typeof publishAdminPublication
>;

function makeExportedState(): EditorState {
  // Walk through the workflow: draft → in_review → approved → exported
  let state = initState();
  const path: EditorAction[] = [
    { type: 'SUBMIT_FOR_REVIEW' },
    { type: 'APPROVE' },
    { type: 'MARK_EXPORTED', filename: 'test.png' },
  ];
  for (const a of path) state = reducer(state, a);
  return state;
}

beforeEach(() => {
  publishMock.mockReset();
});

describe('ReviewPanel — MARK_PUBLISHED publish modal interception', () => {
  it('clicking publish transition opens modal but does NOT dispatch MARK_PUBLISHED', () => {
    const state = makeExportedState();
    const dispatch = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        publicationId="p1"
      />,
    );

    const publishBtn = screen.getByTestId('transition-MARK_PUBLISHED');
    fireEvent.click(publishBtn);

    expect(screen.getByTestId('publish-confirm-modal')).toBeTruthy();
    // No MARK_PUBLISHED dispatch on click — modal is the gate
    expect(
      dispatch.mock.calls.find(
        (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
      ),
    ).toBeUndefined();
  });

  it('modal confirm dispatches MARK_PUBLISHED on successful publish', async () => {
    publishMock.mockResolvedValueOnce({
      etag: 'etag-1',
      document: {} as never,
    });
    const state = makeExportedState();
    const dispatch = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        publicationId="p1"
      />,
    );

    fireEvent.click(screen.getByTestId('transition-MARK_PUBLISHED'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('publish-modal-confirm'));
    });

    expect(publishMock).toHaveBeenCalledTimes(1);
    expect(publishMock).toHaveBeenCalledWith('p1', { bound_blocks: [] });
    const markCalls = dispatch.mock.calls.filter(
      (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
    );
    expect(markCalls).toHaveLength(1);
    expect(markCalls[0][0]).toEqual({
      type: 'MARK_PUBLISHED',
      channel: 'manual',
    });
  });

  it('modal cancel does NOT dispatch any workflow action', () => {
    const state = makeExportedState();
    const dispatch = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        publicationId="p1"
      />,
    );

    fireEvent.click(screen.getByTestId('transition-MARK_PUBLISHED'));
    expect(screen.getByTestId('publish-confirm-modal')).toBeTruthy();
    fireEvent.click(screen.getByTestId('publish-modal-cancel'));

    expect(publishMock).not.toHaveBeenCalled();
    expect(
      dispatch.mock.calls.find(
        (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
      ),
    ).toBeUndefined();
  });

  it('modal confirm with 404 dispatches SAVE_FAILED, not MARK_PUBLISHED, and closes modal', async () => {
    // The jest.mock factory at top of file exports a mocked
    // AdminPublicationNotFoundError class; importing it via `@/lib/api/admin`
    // returns that mocked class, which usePublishAction's `instanceof` check
    // matches.
    publishMock.mockRejectedValueOnce(new AdminPublicationNotFoundError('p1'));

    const state = makeExportedState();
    const dispatch = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        publicationId="p1"
      />,
    );

    fireEvent.click(screen.getByTestId('transition-MARK_PUBLISHED'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('publish-modal-confirm'));
    });

    expect(publishMock).toHaveBeenCalledTimes(1);
    // No MARK_PUBLISHED on 404 — workflow stays in pre-published state
    expect(
      dispatch.mock.calls.find(
        (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
      ),
    ).toBeUndefined();
    // SAVE_FAILED dispatched per ReviewPanel onNotFound handler
    const saveFailedCalls = dispatch.mock.calls.filter(
      (c) => (c[0] as EditorAction).type === 'SAVE_FAILED',
    );
    expect(saveFailedCalls).toHaveLength(1);
    // Modal closes after 404
    expect(screen.queryByTestId('publish-confirm-modal')).toBeNull();
  });

  it('falls back to direct dispatch when publicationId is absent (template-only session, Badge P2-2)', () => {
    const state = makeExportedState();
    const dispatch = jest.fn();
    render(
      <ReviewPanel
        state={state}
        dispatch={dispatch}
        onRequestNote={jest.fn()}
        // publicationId intentionally omitted — template-only editor session
      />,
    );

    fireEvent.click(screen.getByTestId('transition-MARK_PUBLISHED'));

    // No modal — direct path
    expect(screen.queryByTestId('publish-confirm-modal')).toBeNull();
    // No network publish
    expect(publishMock).not.toHaveBeenCalled();
    // Direct MARK_PUBLISHED dispatch (pre-Slice-4a behavior preserved)
    const markCalls = dispatch.mock.calls.filter(
      (c) => (c[0] as EditorAction).type === 'MARK_PUBLISHED',
    );
    expect(markCalls).toHaveLength(1);
    expect(markCalls[0][0]).toEqual({
      type: 'MARK_PUBLISHED',
      channel: 'manual',
    });
  });
});

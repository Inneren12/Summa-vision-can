/**
 * @jest-environment jsdom
 *
 * Tests for the snapshot-based save flow (B2 fix).
 *
 * We test the reducer directly for the core "doc reference at save start
 * vs doc reference at save resolve" logic. A full keyboard-triggered
 * integration test would require mocking the admin API and jsdom's
 * keyboard event pipeline; the reducer-level test isolates the actual
 * invariant (reference equality gates `dirty` clearing).
 */

import { reducer, initState } from '@/components/editor/store/reducer';
import type {
  CanonicalDocument,
  EditorState,
} from '@/components/editor/types';
import { mkDoc, TPLS } from '@/components/editor/registry/templates';

function seededState(): EditorState {
  return { ...initState(), dirty: true };
}

function firstEditableBlockId(state: EditorState): string {
  // headline_editorial is present in single_stat_hero and supports text edits.
  const entry = Object.entries(state.doc.blocks).find(
    ([, b]) => b.type === 'headline_editorial',
  );
  if (!entry) throw new Error('no headline_editorial block in seed');
  return entry[0];
}

describe('SAVED_IF_MATCHES — snapshot gating', () => {
  test('clears dirty when the current doc === snapshotDoc', () => {
    const s0 = seededState();
    const s1 = reducer(s0, {
      type: 'SAVED_IF_MATCHES',
      snapshotDoc: s0.doc,
    });
    expect(s1.dirty).toBe(false);
    expect(s1.saveError).toBeNull();
  });

  test('keeps dirty set when user edited during flight (snapshot stale)', () => {
    const s0 = seededState();
    const blockId = firstEditableBlockId(s0);
    const snapshot: CanonicalDocument = s0.doc;

    // Simulate an edit between save-start and save-resolve. UPDATE_PROP
    // produces a new doc reference so snapshot !== current doc.
    const s1 = reducer(s0, {
      type: 'UPDATE_PROP',
      blockId,
      key: 'text',
      value: 'edited during flight',
    });
    expect(s1.doc).not.toBe(snapshot);

    const s2 = reducer(s1, {
      type: 'SAVED_IF_MATCHES',
      snapshotDoc: snapshot,
    });
    // Edits during flight → backend is now behind UI; dirty must stay set.
    expect(s2.dirty).toBe(true);
    // But the save itself succeeded → no save error.
    expect(s2.saveError).toBeNull();
  });

  test('clears a prior saveError regardless of snapshot match', () => {
    const s0: EditorState = { ...seededState(), saveError: 'prior error' };
    const s1 = reducer(s0, {
      type: 'SAVED_IF_MATCHES',
      snapshotDoc: s0.doc,
    });
    expect(s1.saveError).toBeNull();
  });
});

describe('SAVE_FAILED', () => {
  test('populates state.saveError without touching dirty', () => {
    const s0 = seededState();
    const s1 = reducer(s0, {
      type: 'SAVE_FAILED',
      error: 'Network down',
      canAutoRetry: true,
    });
    expect(s1.saveError).toBe('Network down');
    expect(s1.dirty).toBe(true);
  });
});

describe('DISMISS_SAVE_ERROR', () => {
  test('clears saveError and leaves dirty untouched', () => {
    const s0: EditorState = { ...seededState(), saveError: 'oops' };
    const s1 = reducer(s0, { type: 'DISMISS_SAVE_ERROR' });
    expect(s1.saveError).toBeNull();
    expect(s1.dirty).toBe(true);
  });
});

describe('initState includes saveError: null', () => {
  test('fresh state has null saveError', () => {
    expect(initState().saveError).toBeNull();
  });

  test('initState with seeded doc still has null saveError', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    expect(initState(doc).saveError).toBeNull();
  });
});

// DEBT-027: retry-orchestration state lives in the reducer instead of
// `useRef` + `useEffect([doc])` with an exhaustive-deps disable.
// The "user edited during error → reset retry budget" semantic is
// implemented as a cross-cutting reducer transition: any action that
// produces a new `doc` reference while `state.saveError != null` resets
// `retryAttempt` to 0 and re-arms `canAutoRetry`. UPDATE_PROP is the
// canonical doc-mutating action used to drive these tests.
describe('DEBT-027 — retry-state reducer transitions', () => {
  test('user edit during error state resets retryAttempt to 0 (cross-cutting)', () => {
    const s0Initial = seededState();
    const blockId = firstEditableBlockId(s0Initial);
    const s0: EditorState = {
      ...s0Initial,
      saveError: 'transient network failure',
      retryAttempt: 3,
      canAutoRetry: true,
    };
    const s1 = reducer(s0, {
      type: 'UPDATE_PROP',
      blockId,
      key: 'text',
      value: 'edited during error',
    });
    expect(s1.retryAttempt).toBe(0);
    // Other retry-orchestration fields preserved or re-armed.
    expect(s1.canAutoRetry).toBe(true);
    // `saveError` is intentionally NOT cleared — the banner stays up so
    // the user knows the prior failure happened. The reducer only
    // re-enters the retry cycle; the next save attempt or dismissal
    // clears `saveError`.
    expect(s1.saveError).toBe('transient network failure');
  });

  test('doc edit when no save error is active does NOT change retryAttempt', () => {
    const s0Initial = seededState();
    const blockId = firstEditableBlockId(s0Initial);
    const s0: EditorState = {
      ...s0Initial,
      saveError: null,
      retryAttempt: 3,
      canAutoRetry: true,
    };
    const s1 = reducer(s0, {
      type: 'UPDATE_PROP',
      blockId,
      key: 'text',
      value: 'normal edit, no error active',
    });
    expect(s1.retryAttempt).toBe(3);
    expect(s1.canAutoRetry).toBe(true);
  });

  // The original ref-based design incremented the attempt counter inside
  // the retry timer callback — i.e. when a retry was about to FIRE, not
  // when the prior attempt FAILED. That preserved delay[0] for the first
  // retry. RETRY_ATTEMPT_ADVANCE is the reducer-side replacement for that
  // write; SAVE_FAILED itself does not increment (see reducer comment).
  test('RETRY_ATTEMPT_ADVANCE increments retryAttempt from any starting value', () => {
    const cases = [0, 1, 3, 7];
    for (const start of cases) {
      const s0: EditorState = { ...seededState(), retryAttempt: start };
      const s1 = reducer(s0, { type: 'RETRY_ATTEMPT_ADVANCE' });
      expect(s1.retryAttempt).toBe(start + 1);
    }
  });

  test('SAVED_IF_MATCHES resets retryAttempt to 0', () => {
    const s0Initial = seededState();
    const s0: EditorState = {
      ...s0Initial,
      saveError: 'prior error',
      retryAttempt: 4,
      canAutoRetry: true,
    };
    const s1 = reducer(s0, {
      type: 'SAVED_IF_MATCHES',
      snapshotDoc: s0.doc,
    });
    expect(s1.retryAttempt).toBe(0);
    expect(s1.saveError).toBeNull();
  });
});

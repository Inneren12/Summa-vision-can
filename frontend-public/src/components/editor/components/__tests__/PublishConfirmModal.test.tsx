/**
 * Phase 3.1d Slice 4a — PublishConfirmModal tests.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { PublishConfirmModal } from '../PublishConfirmModal';
import type { Block, CanonicalDocument } from '../../types';
import type { Binding } from '../../binding/types';

const FIXED_TS = '2026-01-01T00:00:00.000Z';

function makeDoc(blocks: Record<string, Block>): CanonicalDocument {
  return {
    schemaVersion: 3,
    templateId: 'test',
    page: {
      size: 'instagram_1080',
      background: 'solid_dark',
      palette: 'housing',
      exportPresets: [],
    },
    sections: [],
    blocks,
    meta: {
      createdAt: FIXED_TS,
      updatedAt: FIXED_TS,
      version: 1,
      history: [],
    },
    review: { workflow: 'draft', history: [], comments: [] },
  } as unknown as CanonicalDocument;
}

function makeBlock(id: string, binding?: Binding, type = 'hero_stat'): Block {
  return {
    id,
    type,
    visible: true,
    props: {},
    ...(binding !== undefined ? { binding } : {}),
  };
}

const validSingle: Binding = {
  kind: 'single',
  cube_id: '18100004',
  semantic_key: 'metric_x',
  filters: { '1': '12' },
  period: '2024-Q3',
};

describe('PublishConfirmModal', () => {
  it('renders nothing when isOpen=false', () => {
    const doc = makeDoc({});
    const { container } = render(
      <PublishConfirmModal
        isOpen={false}
        doc={doc}
        isPublishing={false}
        error={null}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('does not invoke walker when isOpen=false (Badge P2-1)', () => {
    // Behavioral proxy for "walker not called": pass a doc with a
    // malformed-filter binding. If the walker ran, console.warn would
    // fire (per walker.ts non_numeric_filters branch). Asserting the
    // warn count stays at zero proves the early-return guard short-
    // circuits before walkBoundBlocks executes — module-level spying
    // would not catch the bound import inside PublishConfirmModal.
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

    const doc = makeDoc({
      bad: makeBlock('bad', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { geo: 'CA' },
        period: '2024-Q1',
      }),
    });

    render(
      <PublishConfirmModal
        isOpen={false}
        doc={doc}
        isPublishing={false}
        error={null}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );

    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it('renders title + summary when open', () => {
    const doc = makeDoc({ b1: makeBlock('b1', validSingle) });
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing={false}
        error={null}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(screen.getByTestId('publish-confirm-modal')).toBeTruthy();
    expect(
      screen.getByText('publication.publish.modal.title'),
    ).toBeTruthy();
    // Summary key resolves to translation token via the test mock
    expect(
      screen.getByText('publication.publish.modal.summary'),
    ).toBeTruthy();
  });

  it('renders deferred section only when deferred.length > 0', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'time_series',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1': '2' },
        period_range: { last_n: 4 },
      }),
    });
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing={false}
        error={null}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(screen.getByTestId('publish-modal-deferred')).toBeTruthy();
    expect(screen.queryByTestId('publish-modal-skipped')).toBeNull();
  });

  it('renders skipped section only when skipped.length > 0', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { geo: 'CA' },
        period: '2024-Q1',
      }),
    });
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing={false}
        error={null}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(screen.getByTestId('publish-modal-skipped')).toBeTruthy();
    expect(screen.queryByTestId('publish-modal-deferred')).toBeNull();
    warnSpy.mockRestore();
  });

  it('hides both sections when walker has no deferred and no skipped', () => {
    const doc = makeDoc({ b1: makeBlock('b1', validSingle) });
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing={false}
        error={null}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(screen.queryByTestId('publish-modal-deferred')).toBeNull();
    expect(screen.queryByTestId('publish-modal-skipped')).toBeNull();
  });

  it('confirm button calls onConfirm with walker result', () => {
    const doc = makeDoc({ b1: makeBlock('b1', validSingle) });
    const onConfirm = jest.fn();
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing={false}
        error={null}
        onConfirm={onConfirm}
        onCancel={jest.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId('publish-modal-confirm'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    const arg = onConfirm.mock.calls[0][0];
    expect(arg.boundBlocks).toHaveLength(1);
    expect(arg.boundBlocks[0].block_id).toBe('b1');
  });

  it('cancel button calls onCancel', () => {
    const doc = makeDoc({});
    const onCancel = jest.fn();
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing={false}
        error={null}
        onConfirm={jest.fn()}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByTestId('publish-modal-cancel'));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('disables both buttons when isPublishing=true', () => {
    const doc = makeDoc({});
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing
        error={null}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(
      (screen.getByTestId('publish-modal-confirm') as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId('publish-modal-cancel') as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it('confirm button shows publishing label when isPublishing=true', () => {
    const doc = makeDoc({});
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing
        error={null}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(screen.getByTestId('publish-modal-confirm').textContent).toBe(
      'publication.publish.modal.publishing',
    );
  });

  it('renders error banner when error prop is set', () => {
    const doc = makeDoc({});
    render(
      <PublishConfirmModal
        isOpen
        doc={doc}
        isPublishing={false}
        error={new Error('Publish failed: 500')}
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(screen.getByTestId('publish-modal-error').textContent).toBe(
      'Publish failed: 500',
    );
  });
});

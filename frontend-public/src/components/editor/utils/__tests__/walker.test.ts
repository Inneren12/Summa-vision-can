/**
 * Phase 3.1d Slice 4a — walker tests.
 *
 * Pure-function tests; no DOM, no network. Builds minimal CanonicalDocument
 * fixtures that satisfy the type but only the `blocks` field is consulted by
 * the walker.
 */
import { walkBoundBlocks } from '../walker';
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
  filters: { '1': '12', '2': '5' },
  period: '2024-Q3',
};

describe('walkBoundBlocks — happy paths', () => {
  it('returns empty arrays for doc with zero blocks', () => {
    const doc = makeDoc({});
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.deferred).toEqual([]);
    expect(result.skipped).toEqual([]);
  });

  it('returns empty boundBlocks for doc with blocks but no bindings', () => {
    const doc = makeDoc({
      b1: makeBlock('b1'),
      b2: makeBlock('b2', undefined, 'delta_badge'),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.deferred).toEqual([]);
    expect(result.skipped).toEqual([]);
  });

  it('emits BoundBlockReference for hero_stat with valid single binding', () => {
    const doc = makeDoc({ b1: makeBlock('b1', validSingle, 'hero_stat') });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([
      {
        block_id: 'b1',
        cube_id: '18100004',
        semantic_key: 'metric_x',
        dims: [1, 2],
        members: [12, 5],
        period: '2024-Q3',
      },
    ]);
    expect(result.deferred).toEqual([]);
    expect(result.skipped).toEqual([]);
  });

  it('emits BoundBlockReference for delta_badge with valid single binding', () => {
    const doc = makeDoc({ b1: makeBlock('b1', validSingle, 'delta_badge') });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toHaveLength(1);
    expect(result.boundBlocks[0].block_id).toBe('b1');
  });

  it('emits dims/members in numeric ascending order (Slice 4a fix P1-3)', () => {
    const binding: Binding = {
      kind: 'single',
      cube_id: 'c1',
      semantic_key: 's1',
      filters: { '10': '100', '2': '20', '3': '30' },
      period: '2024-Q1',
    };
    const doc = makeDoc({ b1: makeBlock('b1', binding) });
    const result = walkBoundBlocks(doc);
    // Numeric sort: 2 < 3 < 10 (was lexicographic '10' < '2' < '3' pre-fix).
    // Pairing stays positional: dim[i] ↔ member[i].
    expect(result.boundBlocks[0].dims).toEqual([2, 3, 10]);
    expect(result.boundBlocks[0].members).toEqual([20, 30, 100]);
  });

  it('handles empty filters: {} → dims=[], members=[]', () => {
    const binding: Binding = {
      kind: 'single',
      cube_id: 'c1',
      semantic_key: 's1',
      filters: {},
      period: '2024-Q1',
    };
    const doc = makeDoc({ b1: makeBlock('b1', binding) });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([
      {
        block_id: 'b1',
        cube_id: 'c1',
        semantic_key: 's1',
        dims: [],
        members: [],
        period: '2024-Q1',
      },
    ]);
  });

  it('handles multiple single bindings in one doc', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', validSingle),
      b2: makeBlock(
        'b2',
        {
          kind: 'single',
          cube_id: '18100002',
          semantic_key: 'other_metric',
          filters: { '7': '88' },
          period: '2024-Q2',
        },
        'delta_badge',
      ),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toHaveLength(2);
    const ids = result.boundBlocks.map((b) => b.block_id).sort();
    expect(ids).toEqual(['b1', 'b2']);
  });
});

describe('walkBoundBlocks — block-type allowlist (Slice 4a fix P1-1)', () => {
  it('skips single binding on unsupported block type (e.g. headline_editorial)', () => {
    const doc = makeDoc({
      h1: makeBlock('h1', validSingle, 'headline_editorial'),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.skipped).toEqual([
      { block_id: 'h1', reason: 'unsupported_block_type' },
    ]);
    expect(result.deferred).toEqual([]);
  });

  it('skips single binding on unsupported block type (e.g. bar_horizontal)', () => {
    const doc = makeDoc({
      bar1: makeBlock('bar1', validSingle, 'bar_horizontal'),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.skipped).toEqual([
      { block_id: 'bar1', reason: 'unsupported_block_type' },
    ]);
  });

  it('emits hero_stat with valid single binding (allowlist enforced)', () => {
    const doc = makeDoc({ b1: makeBlock('b1', validSingle, 'hero_stat') });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toHaveLength(1);
    expect(result.skipped).toEqual([]);
  });

  it('emits delta_badge with valid single binding (allowlist enforced)', () => {
    const doc = makeDoc({ b1: makeBlock('b1', validSingle, 'delta_badge') });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toHaveLength(1);
    expect(result.skipped).toEqual([]);
  });
});

describe('walkBoundBlocks — deferred (unsupported kinds)', () => {
  it('emits time_series binding to deferred, not boundBlocks', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'time_series',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1': '2' },
        period_range: { from: '2023-Q1', to: '2024-Q1' },
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.deferred).toEqual([{ block_id: 'b1', kind: 'time_series' }]);
    expect(result.skipped).toEqual([]);
  });

  it('emits categorical_series binding to deferred', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'categorical_series',
        cube_id: 'c1',
        semantic_key: 's1',
        category_dim: 'geo',
        filters: { '1': '2' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.deferred).toEqual([
      { block_id: 'b1', kind: 'categorical_series' },
    ]);
  });

  it('emits multi_metric binding to deferred', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'multi_metric',
        cube_id: 'c1',
        metrics: [{ semantic_key: 'm1' }, { semantic_key: 'm2' }],
        filters: { '1': '2' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.deferred).toEqual([
      { block_id: 'b1', kind: 'multi_metric' },
    ]);
  });

  it('emits tabular binding to deferred', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'tabular',
        cube_id: 'c1',
        columns: [{ semantic_key: 'col1' }],
        row_dim: 'geo',
        filters: { '1': '2' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.deferred).toEqual([{ block_id: 'b1', kind: 'tabular' }]);
  });
});

describe('walkBoundBlocks — skipped (malformed)', () => {
  let warnSpy: jest.SpyInstance;
  beforeEach(() => {
    warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });
  afterEach(() => {
    warnSpy.mockRestore();
  });

  it('drops block with non-numeric filter key (e.g. "geo")', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { geo: '12' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.skipped).toEqual([
      { block_id: 'b1', reason: 'non_numeric_filters' },
    ]);
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it('drops block with non-numeric filter value (e.g. "CA")', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1': 'CA' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.skipped).toEqual([
      { block_id: 'b1', reason: 'non_numeric_filters' },
    ]);
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it('logs console.warn with block_id and filters payload', () => {
    const doc = makeDoc({
      bad_block: makeBlock('bad_block', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1': 'not_a_number' },
        period: '2024-Q1',
      }),
    });
    walkBoundBlocks(doc);
    expect(warnSpy).toHaveBeenCalledTimes(1);
    const message = warnSpy.mock.calls[0][0] as string;
    expect(message).toContain('bad_block');
    expect(message).toContain('not_a_number');
  });

  it('drops block with float in filter key (e.g. "1.5")', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1.5': '12' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.skipped).toEqual([
      { block_id: 'b1', reason: 'non_numeric_filters' },
    ]);
  });

  it('drops block with float in filter value (e.g. "12.5")', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1': '12.5' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([]);
    expect(result.skipped).toEqual([
      { block_id: 'b1', reason: 'non_numeric_filters' },
    ]);
  });

  it('drops block with empty-string filter key', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '': '12' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.skipped).toEqual([
      { block_id: 'b1', reason: 'non_numeric_filters' },
    ]);
  });

  it('drops block with empty-string filter value', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1': '' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.skipped).toEqual([
      { block_id: 'b1', reason: 'non_numeric_filters' },
    ]);
  });

  it('drops block with whitespace filter key (e.g. " ")', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { ' ': '12' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.skipped).toEqual([
      { block_id: 'b1', reason: 'non_numeric_filters' },
    ]);
  });

  it('drops block with leading-zero filter value (e.g. "01")', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1': '01' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.skipped).toEqual([
      { block_id: 'b1', reason: 'non_numeric_filters' },
    ]);
  });

  it('accepts "0" as valid filter token', () => {
    const doc = makeDoc({
      b1: makeBlock('b1', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '0': '0' },
        period: '2024-Q1',
      }),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toEqual([
      {
        block_id: 'b1',
        cube_id: 'c1',
        semantic_key: 's1',
        dims: [0],
        members: [0],
        period: '2024-Q1',
      },
    ]);
    expect(result.skipped).toEqual([]);
  });
});

describe('walkBoundBlocks — mixed', () => {
  let warnSpy: jest.SpyInstance;
  beforeEach(() => {
    warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });
  afterEach(() => {
    warnSpy.mockRestore();
  });

  it('emits boundBlocks + deferred + skipped from same doc correctly', () => {
    const doc = makeDoc({
      good: makeBlock('good', validSingle),
      ts: makeBlock('ts', {
        kind: 'time_series',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { '1': '2' },
        period_range: { last_n: 4 },
      }),
      bad: makeBlock('bad', {
        kind: 'single',
        cube_id: 'c1',
        semantic_key: 's1',
        filters: { geo: 'CA' },
        period: '2024-Q1',
      }),
      no_binding: makeBlock('no_binding'),
    });
    const result = walkBoundBlocks(doc);
    expect(result.boundBlocks).toHaveLength(1);
    expect(result.boundBlocks[0].block_id).toBe('good');
    expect(result.deferred).toEqual([{ block_id: 'ts', kind: 'time_series' }]);
    expect(result.skipped).toEqual([
      { block_id: 'bad', reason: 'non_numeric_filters' },
    ]);
  });
});

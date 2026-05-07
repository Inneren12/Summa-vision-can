import {
  aggregateCompareSeverity,
  aggregateReasons,
  countReason,
  shouldShowRepublishCtaForDoc,
  summarizeCompare,
} from '../compareSeverity';
import type { Block, CanonicalDocument } from '@/components/editor/types';
import type {
  BlockComparatorResult,
  CompareResponse,
  StaleReason,
  StaleStatus,
} from '@/lib/types/compare';

function block(
  id: string,
  stale_status: StaleStatus,
  stale_reasons: StaleReason[] = [],
): BlockComparatorResult {
  return {
    block_id: id,
    cube_id: 'cube_x',
    semantic_key: 'metric_y',
    stale_status,
    stale_reasons,
    severity: 'info',
    compared_at: '2026-05-04T00:00:00Z',
    snapshot: null,
    current: null,
    compare_basis: {
      compare_kind: 'drift_check',
      matched_fields: [],
      drift_fields: [],
    },
  };
}

function response(
  blocks: BlockComparatorResult[],
  overall: StaleStatus = 'fresh',
): CompareResponse {
  return {
    publication_id: 1,
    overall_status: overall,
    overall_severity: 'info',
    compared_at: '2026-05-04T00:00:00Z',
    block_results: blocks,
  };
}

describe('aggregateCompareSeverity', () => {
  it('falls back to overall_status (fresh) for empty block_results', () => {
    expect(aggregateCompareSeverity(response([], 'fresh'))).toBe('fresh');
  });

  it('falls back to overall_status (unknown) for empty block_results', () => {
    expect(aggregateCompareSeverity(response([], 'unknown'))).toBe('unknown');
  });

  it('falls back to overall_status (stale) for empty block_results', () => {
    expect(aggregateCompareSeverity(response([], 'stale'))).toBe('stale');
  });

  it('returns fresh when all blocks fresh and overall fresh', () => {
    expect(
      aggregateCompareSeverity(response([block('a', 'fresh')], 'fresh')),
    ).toBe('fresh');
  });

  it('returns stale when overall_status is stale', () => {
    expect(
      aggregateCompareSeverity(
        response([block('a', 'stale', ['value_changed'])], 'stale'),
      ),
    ).toBe('stale');
  });

  it('returns missing when any block has snapshot_missing reason', () => {
    expect(
      aggregateCompareSeverity(
        response(
          [block('a', 'unknown', ['snapshot_missing']), block('b', 'fresh')],
          'unknown',
        ),
      ),
    ).toBe('missing');
  });

  it('returns partial when any block has compare_failed reason', () => {
    expect(
      aggregateCompareSeverity(
        response(
          [block('a', 'unknown', ['compare_failed']), block('b', 'fresh')],
          'unknown',
        ),
      ),
    ).toBe('partial');
  });

  it('compare_failed precedence beats snapshot_missing', () => {
    expect(
      aggregateCompareSeverity(
        response(
          [
            block('a', 'unknown', ['snapshot_missing']),
            block('b', 'unknown', ['compare_failed']),
          ],
          'unknown',
        ),
      ),
    ).toBe('partial');
  });
});

describe('countReason', () => {
  it('counts blocks containing the given reason', () => {
    const r = response([
      block('a', 'unknown', ['compare_failed']),
      block('b', 'unknown', ['compare_failed', 'value_changed']),
      block('c', 'fresh'),
    ]);
    expect(countReason(r, 'compare_failed')).toBe(2);
    expect(countReason(r, 'value_changed')).toBe(1);
    expect(countReason(r, 'snapshot_missing')).toBe(0);
  });
});

describe('aggregateReasons (Slice 5)', () => {
  it('returns empty array for empty block_results', () => {
    expect(aggregateReasons([])).toEqual([]);
  });

  it('deduplicates the same reason across blocks', () => {
    expect(
      aggregateReasons([
        block('a', 'stale', ['value_changed']),
        block('b', 'stale', ['value_changed']),
      ]),
    ).toEqual(['value_changed']);
  });

  it('returns reasons in stable enum-declaration order regardless of input order', () => {
    expect(
      aggregateReasons([
        block('a', 'stale', ['snapshot_missing', 'mapping_version_changed']),
        block('b', 'stale', ['cache_row_stale']),
      ]),
    ).toEqual(['mapping_version_changed', 'cache_row_stale', 'snapshot_missing']);
  });

  it('handles all 7 reasons present', () => {
    const all: StaleReason[] = [
      'mapping_version_changed',
      'source_hash_changed',
      'value_changed',
      'missing_state_changed',
      'cache_row_stale',
      'compare_failed',
      'snapshot_missing',
    ];
    expect(aggregateReasons([block('a', 'stale', all)])).toEqual(all);
    expect(aggregateReasons([block('a', 'stale', all)])).toHaveLength(7);
  });

  it('skips blocks with no reasons', () => {
    expect(
      aggregateReasons([
        block('a', 'fresh'),
        block('b', 'stale', ['value_changed']),
      ]),
    ).toEqual(['value_changed']);
  });
});

function makeBlock(type: string, binding?: Block['binding']): Block {
  return {
    id: 'unused',
    type,
    props: {},
    visible: true,
    binding,
  } as Block;
}

function makeDoc(blocks: Record<string, Block>): CanonicalDocument {
  return {
    schemaVersion: 3,
    templateId: 'single_stat_hero',
    page: {
      size: 'instagram_square',
      background: '#ffffff',
      palette: 'default',
      exportPresets: [],
    },
    sections: [],
    blocks,
    meta: { version: 1 },
    review: {
      workflow: 'draft',
      history: [],
      comments: [],
    },
  } as unknown as CanonicalDocument;
}

const heroSingle: Block['binding'] = {
  kind: 'single',
  cube_id: 'c1',
  semantic_key: 's1',
  filters: {},
  period: '2024-Q3',
};

const synthetic: BlockComparatorResult = {
  block_id: '',
  cube_id: '',
  semantic_key: '',
  stale_status: 'unknown',
  stale_reasons: ['snapshot_missing'],
  severity: 'info',
  compared_at: '2026-05-07T00:00:00Z',
  snapshot: null,
  current: null,
  compare_basis: { compare_kind: 'snapshot_missing', cause: 'no_snapshot_row' },
};

describe('shouldShowRepublishCtaForDoc (Slice 5 R2)', () => {
  it('returns false when doc has no v1 bindable blocks (editorial-only publication)', () => {
    const doc = makeDoc({ b1: makeBlock('paragraph') });
    // synthetic snapshot_missing must NOT trigger the CTA without intent
    expect(shouldShowRepublishCtaForDoc(doc, [synthetic])).toBe(false);
    expect(shouldShowRepublishCtaForDoc(doc, [])).toBe(false);
  });

  it('returns true when doc has hero_stat single binding + empty block_results (pre-3.1d legacy)', () => {
    const doc = makeDoc({ b1: makeBlock('hero_stat', heroSingle) });
    expect(shouldShowRepublishCtaForDoc(doc, [])).toBe(true);
  });

  it('returns true when doc has hero_stat + synthetic publication-level snapshot_missing', () => {
    const doc = makeDoc({ b1: makeBlock('hero_stat', heroSingle) });
    expect(shouldShowRepublishCtaForDoc(doc, [synthetic])).toBe(true);
  });

  it('returns false when bindable blocks have fresh snapshots', () => {
    const doc = makeDoc({ b1: makeBlock('hero_stat', heroSingle) });
    const fresh: BlockComparatorResult = {
      ...block('b1', 'fresh'),
      // override block_id to match the doc binding ID
    };
    fresh.block_id = 'b1';
    expect(shouldShowRepublishCtaForDoc(doc, [fresh])).toBe(false);
  });

  it('returns true when one bindable block lacks any backend result', () => {
    const doc = makeDoc({
      b1: makeBlock('hero_stat', heroSingle),
      b2: makeBlock('hero_stat', heroSingle),
    });
    const onlyB1: BlockComparatorResult = block('b1', 'fresh');
    // b2 has no result → operator added it post-publish, snapshot missing
    expect(shouldShowRepublishCtaForDoc(doc, [onlyB1])).toBe(true);
  });

  it('returns true when bindable block has per-block snapshot_missing reason', () => {
    const doc = makeDoc({ b1: makeBlock('hero_stat', heroSingle) });
    const missing: BlockComparatorResult = block('b1', 'unknown', [
      'snapshot_missing',
    ]);
    expect(shouldShowRepublishCtaForDoc(doc, [missing])).toBe(true);
  });

  it('returns false for time_series only (not v1 single-bindable type)', () => {
    const doc = makeDoc({
      b1: makeBlock('time_series', heroSingle),
    });
    expect(shouldShowRepublishCtaForDoc(doc, [])).toBe(false);
  });

  it('returns false for hero_stat with non-single binding kind', () => {
    const doc = makeDoc({
      b1: makeBlock('hero_stat', {
        kind: 'multi_metric',
        cube_id: 'c1',
        metrics: [{ semantic_key: 's1' }],
        filters: {},
        period: '2024-Q3',
      }),
    });
    expect(shouldShowRepublishCtaForDoc(doc, [])).toBe(false);
  });

  it('ignores backend rows for unbound blocks (operator unbound after last publish)', () => {
    const doc = makeDoc({
      b1: makeBlock('hero_stat', heroSingle),
    });
    // backend has fresh result for b1 + a stray result for an old block
    // the operator has since unbound; CTA should NOT trigger.
    const fresh: BlockComparatorResult = block('b1', 'fresh');
    const stray: BlockComparatorResult = block('b_old', 'unknown', [
      'snapshot_missing',
    ]);
    expect(shouldShowRepublishCtaForDoc(doc, [fresh, stray])).toBe(false);
  });
});

describe('summarizeCompare', () => {
  it('counts stale blocks uniquely (no double-count)', () => {
    const r = response(
      [
        block('a', 'stale', ['value_changed', 'source_hash_changed']),
        block('b', 'stale', ['mapping_version_changed']),
        block('c', 'fresh'),
      ],
      'stale',
    );
    const summary = summarizeCompare(r);
    expect(summary.total).toBe(3);
    // a + b counted as stale (a once, despite two stale reasons)
    expect(summary.stale).toBe(2);
    expect(summary.missing).toBe(0);
    expect(summary.failed).toBe(0);
  });
});

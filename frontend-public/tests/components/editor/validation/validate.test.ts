/**
 * Phase 2.1 PR#4 — split tests for the validation module.
 *
 * Existing baseline coverage of `validate(doc)` lives in
 * `tests/editor/validate.test.ts` (untouched). This file covers the new
 * `validateDocument` / `validatePresetSize` split + back-compat wrapper
 * contract per the PR#4 implementation prompt.
 */

import {
  validate,
  validateDocument,
  validatePresetSize,
} from '@/components/editor/validation/validate';
import { TPLS, mkDoc } from '@/components/editor/registry/templates';
import type { CanonicalDocument } from '@/components/editor/types';
import type { PresetId } from '@/components/editor/config/sizes';

// Mock the renderToBlob module so the long-infographic cap can be driven from
// the test rather than requiring the test to construct a 4000-px-tall doc.
// The `...actual` spread keeps the real `LONG_INFOGRAPHIC_HEIGHT_CAP` value;
// we only override `computeLongInfographicHeight` to return whatever the
// individual case needs. validate.ts imports both from this module, so the
// validator under test sees the same mocked function.
jest.mock('@/components/editor/export/renderToBlob', () => {
  const actual = jest.requireActual(
    '@/components/editor/export/renderToBlob',
  );
  return {
    ...actual,
    computeLongInfographicHeight: jest.fn(actual.computeLongInfographicHeight),
  };
});

import { computeLongInfographicHeight } from '@/components/editor/export/renderToBlob';

const mockedCompute = computeLongInfographicHeight as jest.MockedFunction<
  typeof computeLongInfographicHeight
>;

function cloneDoc(tid: keyof typeof TPLS): CanonicalDocument {
  return JSON.parse(JSON.stringify(mkDoc(tid as string, TPLS[tid as string])));
}

describe('validation split (PR#4)', () => {
  beforeEach(() => {
    // Default to passing through to the real implementation. Tests that need
    // an overflow scenario override per-call.
    mockedCompute.mockImplementation((doc, width) => {
      const actual = jest.requireActual(
        '@/components/editor/export/renderToBlob',
      );
      return actual.computeLongInfographicHeight(doc, width);
    });
  });

  test('validateDocument output is identical regardless of doc.page.size', () => {
    const docA = cloneDoc('single_stat_hero');
    const docB: CanonicalDocument = {
      ...docA,
      page: { ...docA.page, size: 'twitter_landscape' },
    };
    const a = validateDocument(docA);
    const b = validateDocument(docB);
    // Compare arrays as JSON to confirm identical output (order-sensitive).
    expect(JSON.stringify(a.errors)).toBe(JSON.stringify(b.errors));
    expect(JSON.stringify(a.warnings)).toBe(JSON.stringify(b.warnings));
    expect(JSON.stringify(a.info)).toBe(JSON.stringify(b.info));
    expect(JSON.stringify(a.passed)).toBe(JSON.stringify(b.passed));
  });

  test('validatePresetSize: long_infographic over cap → error; instagram_1080 → no cap error', () => {
    // Force a measured height above the 4000 cap so the validator emits the
    // pre-render error. Instagram_1080 must NEVER trigger the long-infographic
    // cap branch since the rule is preset-scoped.
    mockedCompute.mockReturnValue(4500);

    const doc = cloneDoc('single_stat_hero');

    const longResult = validatePresetSize(doc, 'long_infographic');
    expect(longResult.errors.length).toBeGreaterThan(0);
    expect(longResult.errors[0].key).toBe(
      'validation.long_infographic.height_cap_exceeded',
    );

    const igResult = validatePresetSize(doc, 'instagram_1080');
    const igHasCapError = igResult.errors.some(
      (e) => e.key === 'validation.long_infographic.height_cap_exceeded',
    );
    expect(igHasCapError).toBe(false);
  });

  test('validatePresetSize: long_infographic under cap → no error', () => {
    mockedCompute.mockReturnValue(3500);
    const doc = cloneDoc('single_stat_hero');
    const longResult = validatePresetSize(doc, 'long_infographic');
    const hasCapError = longResult.errors.some(
      (e) => e.key === 'validation.long_infographic.height_cap_exceeded',
    );
    expect(hasCapError).toBe(false);
  });

  test('validate(doc) === merge(validateDocument, validatePresetSize) for current size', () => {
    const doc = cloneDoc('single_stat_hero');
    const wrapped = validate(doc);
    const docResult = validateDocument(doc);
    const sizeResult = validatePresetSize(doc, doc.page.size as PresetId);

    expect(wrapped.errors).toEqual([
      ...docResult.errors,
      ...sizeResult.errors,
    ]);
    expect(wrapped.warnings).toEqual([
      ...docResult.warnings,
      ...sizeResult.warnings,
    ]);
    expect(wrapped.info).toEqual([
      ...docResult.info,
      ...sizeResult.info,
    ]);
    expect(wrapped.passed).toEqual([
      ...docResult.passed,
      ...sizeResult.passed,
    ]);
    expect(wrapped.contrastIssues).toEqual([
      ...docResult.contrastIssues,
      ...sizeResult.contrastIssues,
    ]);
  });

  test('validatePresetSize: REAL over-cap long_infographic doc emits cap error (no mocks, validator/renderer parity)', () => {
    // PR#4 fix1 — closes a memory #5 gap. The other tests in this file mock
    // computeLongInfographicHeight via mockedCompute.mockReturnValue. That
    // covers the validator's branch logic but does NOT prove the validator
    // and renderer agree on what counts as "over cap" for a real document.
    //
    // This test runs validatePresetSize against the REAL implementation by
    // overriding the mock to pass through. If a future refactor of
    // computeLongInfographicHeight ever changes its return contract (e.g.
    // an internal clamp at MAX), the mocked tests would still pass while
    // production silently breaks. This test catches that.
    const actual = jest.requireActual(
      '@/components/editor/export/renderToBlob',
    );
    mockedCompute.mockImplementation(actual.computeLongInfographicHeight);

    // Build a doc with enough body_annotation blocks to push real measured
    // height past LONG_INFOGRAPHIC_HEIGHT_CAP (4000px) when measured at the
    // long_infographic preset width (1200). The exact threshold depends on
    // per-block height in measureLayout output; 60 blocks of moderate text
    // is comfortably above 4000px in any reasonable layout.
    //
    // If this count needs adjustment (real height under cap), increase in
    // increments of 20 until cap is exceeded. DO NOT switch to mocking the
    // height — that defeats the purpose of this test.
    const doc = cloneDoc('single_stat_hero');
    const firstSection = doc.sections[0];
    if (!firstSection) {
      throw new Error(
        'cloneDoc("single_stat_hero") produced no sections — fixture changed; update test',
      );
    }
    for (let i = 0; i < 60; i += 1) {
      const id = `pr4_fix1_overflow_block_${i}`;
      doc.blocks[id] = {
        id,
        type: 'body_annotation',
        visible: true,
        props: {
          text: 'Real-cap regression filler text for PR#4 fix1. '.repeat(8),
        },
      };
      firstSection.blockIds.push(id);
    }

    const result = validatePresetSize(doc, 'long_infographic');

    // The error must fire — this is the parity contract.
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        key: 'validation.long_infographic.height_cap_exceeded',
      }),
    );

    // Additionally assert the measured value is realistic (>4000), not a
    // 0 or NaN that accidentally matches >4000 in some narrow case. This
    // catches a class of regression where computeLongInfographicHeight
    // returns garbage that still trips the >cap branch.
    const capError = result.errors.find(
      (e) => e.key === 'validation.long_infographic.height_cap_exceeded',
    );
    expect(capError).toBeDefined();
    const measured = capError!.params?.measured;
    expect(typeof measured).toBe('number');
    expect(measured).toBeGreaterThan(4000);
    expect(Number.isFinite(measured)).toBe(true);
  });
});

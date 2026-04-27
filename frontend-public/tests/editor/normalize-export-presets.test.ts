/**
 * PR#2 fix1 (BLOCKER-2): `normalizeExportPresets` is the single source of
 * truth for the "current canvas size always present in `page.exportPresets`"
 * invariant. The pre-fix implementation only enforced this in the UI (a
 * disabled-checked checkbox in `ExportPresetsSection`), which left
 * `state.doc.page.exportPresets` free to drift through the reducer or
 * partial migrations and produce a ZIP missing the working canvas.
 *
 * The reducer (`UPDATE_PAGE_EXPORT_PRESETS` + `CHANGE_PAGE` size case) and
 * the v2 → v3 migration both call this helper, so the invariant holds for
 * every entry point that can write to `exportPresets`.
 */

import {
  normalizeExportPresets,
  DEFAULT_EXPORT_PRESETS,
} from '@/components/editor/config/sizes';

describe('normalizeExportPresets', () => {
  test('always includes the current canvas size, even if absent from input', () => {
    // The operator can never produce a ZIP that excludes the working canvas:
    // the reducer re-injects the current size on every write.
    const result = normalizeExportPresets(['twitter_landscape'], 'instagram_portrait');

    expect(result).toContain('instagram_portrait');
    expect(result).toContain('twitter_landscape');
  });

  test('filters unknown preset IDs out', () => {
    // Garbage from JSON imports, legacy beta data, or a partial migration
    // is silently dropped. Known IDs survive; the current size is added.
    const result = normalizeExportPresets(
      ['twitter_landscape', 'garbage_id_does_not_exist'],
      'instagram_1080',
    );

    expect(result).toContain('twitter_landscape');
    expect(result).toContain('instagram_1080');
    expect(result).not.toContain('garbage_id_does_not_exist');
  });

  test('uses DEFAULT_EXPORT_PRESETS when input is undefined', () => {
    // Undefined input → fall back to the common-4 default. With the current
    // size already in that default the result is the default itself.
    const result = normalizeExportPresets(undefined, 'instagram_1080');

    expect(result).toContain('instagram_1080');
    expect(result).toContain('twitter_landscape');
    expect(result).toContain('reddit_standard');
    expect(result).toContain('linkedin_landscape');
    expect(result).toEqual([...DEFAULT_EXPORT_PRESETS]);
  });

  test('deduplicates: current size already in input list yields no duplicate', () => {
    // The "force-include current size" step is idempotent — re-adding an
    // already-present id must NOT produce a duplicate, since downstream
    // PR#3 ZIP packaging keys filenames by preset id.
    const result = normalizeExportPresets(
      ['instagram_1080', 'twitter_landscape'],
      'instagram_1080',
    );

    const count = result.filter((id) => id === 'instagram_1080').length;
    expect(count).toBe(1);
  });
});

/**
 * Phase 2.3 — UTM attribution capture tests.
 */
import {
  captureUtmFromUrl,
  getStoredUtm,
} from '@/lib/attribution/utm';

const STORAGE_KEY = 'utm_attribution';

function setLocationSearch(search: string) {
  // Use pushState — jsdom forbids redefining window.location after first
  // access, but it does honor history navigation.
  window.history.pushState({}, '', `/page${search}`);
}

describe('captureUtmFromUrl', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/');
    window.sessionStorage.clear();
  });

  it('returns empty object when URL has no UTM params and storage is empty', () => {
    expect(captureUtmFromUrl()).toEqual({});
  });

  it('captures all four UTM keys from URL into sessionStorage', () => {
    setLocationSearch(
      '?utm_source=reddit&utm_medium=social&utm_campaign=publish_kit&utm_content=ln_xyz',
    );
    const utm = captureUtmFromUrl();
    expect(utm).toEqual({
      utm_source: 'reddit',
      utm_medium: 'social',
      utm_campaign: 'publish_kit',
      utm_content: 'ln_xyz',
    });
    expect(JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) || '{}')).toEqual(
      utm,
    );
  });

  it('does not clobber stored UTM when called on a clean URL', () => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ utm_content: 'ln_persistent' }),
    );
    setLocationSearch('');
    expect(captureUtmFromUrl()).toEqual({ utm_content: 'ln_persistent' });
  });

  it('replaces stored UTM when new URL params are present', () => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ utm_content: 'ln_old', utm_source: 'twitter' }),
    );

    setLocationSearch('?utm_source=reddit&utm_content=ln_new');

    expect(captureUtmFromUrl()).toEqual({
      utm_source: 'reddit',
      utm_content: 'ln_new',
    });
    // utm_content from old session is GONE — no mixing.
  });
});

describe('getStoredUtm', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('returns {} when storage is empty', () => {
    expect(getStoredUtm()).toEqual({});
  });

  it('returns {} when storage contains malformed JSON', () => {
    window.sessionStorage.setItem(STORAGE_KEY, 'not-json');
    expect(getStoredUtm()).toEqual({});
  });

  it('ignores non-string values defensively', () => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ utm_source: 'reddit', utm_content: 42 }),
    );
    expect(getStoredUtm()).toEqual({ utm_source: 'reddit' });
  });
});

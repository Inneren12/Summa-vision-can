/**
 * Phase 2.3 — UTM attribution capture tests.
 */
import {
  captureUtmFromUrl,
  getStoredUtm,
} from '@/lib/attribution/utm';

const STORAGE_KEY = 'utm_attribution';

function setLocationSearch(search: string) {
  const url = new URL(`https://summa-vision.test/page${search}`);
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: url,
  });
}

describe('captureUtmFromUrl', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    setLocationSearch('');
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

  it('merges new URL params with previously stored values', () => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ utm_content: 'ln_old' }),
    );
    setLocationSearch('?utm_source=reddit');
    const utm = captureUtmFromUrl();
    expect(utm).toEqual({
      utm_content: 'ln_old',
      utm_source: 'reddit',
    });
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

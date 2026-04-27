import { getCropZoneForPreset } from '@/components/editor/config/cropZones';

describe('getCropZoneForPreset', () => {
  test('returns null for instagram_story preset', () => {
    expect(getCropZoneForPreset('instagram_story')).toBeNull();
  });

  test('returns full-canvas zone for reddit_standard preset', () => {
    const zone = getCropZoneForPreset('reddit_standard');
    expect(zone).not.toBeNull();
    expect(zone?.platform).toBe('reddit');
    expect(zone?.w).toBe(1200);
    expect(zone?.h).toBe(900);
  });

  test('returns reddit zone for instagram_1080 preset', () => {
    const zone = getCropZoneForPreset('instagram_1080');
    expect(zone).not.toBeNull();
    expect(zone?.platform).toBe('reddit');
    expect(zone?.w).toBe(1080);
    expect(zone?.h).toBe(810);
  });

  test('returns reddit zone for instagram_portrait preset', () => {
    const zone = getCropZoneForPreset('instagram_portrait');
    expect(zone).not.toBeNull();
    expect(zone?.platform).toBe('reddit');
  });

  test('returns null for unknown preset', () => {
    expect(getCropZoneForPreset('unknown_preset_id')).toBeNull();
  });

  test('multi-platform priority loop prefers reddit first', () => {
    const zone = getCropZoneForPreset('instagram_1080');
    expect(zone?.platform).toBe('reddit');
  });
});

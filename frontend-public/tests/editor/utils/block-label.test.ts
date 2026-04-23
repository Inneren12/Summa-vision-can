import { resolveBlockLabel } from '../../../src/components/editor/utils/block-label';

describe('resolveBlockLabel', () => {
  it('returns generic fallback when blockType is undefined', () => {
    const tBlockType = jest.fn();
    const tReview = jest.fn((key: string) => key);
    expect(resolveBlockLabel(undefined, tBlockType, tReview)).toBe('comment.block_generic');
    expect(tBlockType).not.toHaveBeenCalled();
  });

  it('returns translated name when catalog has the key', () => {
    const tBlockType = jest.fn((key: string) => {
      if (key === 'hero_stat.name') return 'Ключевой показатель';
      return key;
    });
    const tReview = jest.fn();
    expect(resolveBlockLabel('hero_stat', tBlockType, tReview)).toBe('Ключевой показатель');
  });

  it('falls back to blockDisplayLabel when translation is missing', () => {
    const tBlockType = jest.fn((key: string) => key);
    const tReview = jest.fn();
    expect(resolveBlockLabel('foo_experimental', tBlockType, tReview)).toBe('foo_experimental');
  });
});

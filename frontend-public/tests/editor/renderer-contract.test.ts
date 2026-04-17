import { BR } from '../../src/components/editor/renderer/blocks';

function makeCtx() {
  const gradient = {
    addColorStop: jest.fn(),
  };
  return {
    font: '',
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 1,
    textAlign: 'left',
    globalAlpha: 1,
    setLineDash: jest.fn(),
    beginPath: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    stroke: jest.fn(),
    fill: jest.fn(),
    fillRect: jest.fn(),
    roundRect: jest.fn(),
    fillText: jest.fn(),
    strokeRect: jest.fn(),
    rect: jest.fn(),
    clip: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    closePath: jest.fn(),
    arc: jest.fn(),
    ellipse: jest.fn(),
    measureText: jest.fn((text: string) => ({ width: (text || '').length * 7 })),
    createLinearGradient: jest.fn(() => gradient),
    createRadialGradient: jest.fn(() => gradient),
    createPattern: jest.fn(() => null),
  } as any;
}

describe('renderer contract', () => {
  test('every block renderer returns a RenderResult', () => {
    const ctx = makeCtx();
    const pal = { p: '#00f', s: '#0ff', a: '#ff0', pos: '#0a0', neg: '#f00' };

    for (const [, fn] of Object.entries(BR)) {
      const result = fn(ctx, {}, 0, 0, 800, 200, pal, 1);
      expect(result).toHaveProperty('height');
      expect(result).toHaveProperty('overflow');
      expect(result).toHaveProperty('warnings');
      expect(result).toHaveProperty('hitArea');
      expect(typeof result.height).toBe('number');
      expect(typeof result.overflow).toBe('boolean');
      expect(Array.isArray(result.warnings)).toBe(true);
    }
  });

  test('bar_horizontal reports overflow when items exceed section height', () => {
    const ctx = makeCtx();
    const pal = { p: '#00f', s: '#0ff', a: '#ff0', pos: '#0a0', neg: '#f00' };

    const manyItems = Array.from({ length: 20 }, (_, i) => ({
      label: `Item ${i}`,
      value: i + 1,
      flag: '🇨🇦',
      highlight: false,
    }));

    const result = BR.bar_horizontal(ctx, { items: manyItems, unit: '%' }, 0, 0, 800, 150, pal, 1);
    expect(result.overflow).toBe(true);
    expect(result.warnings.length).toBeGreaterThan(0);
  });
});

/**
 * @jest-environment jsdom
 *
 * Wiring test for the canvas click-to-select pathway (Stage 4 Task 1).
 *
 * jsdom's HTMLCanvasElement returns null from getContext('2d'), so the
 * content render effect exits before renderDoc populates hit areas. We
 * therefore assert the wiring (two canvases, pointer-events, empty-space
 * dispatch) rather than hit-hit behaviour, which is covered as a pure
 * unit test in `hit-test.test.ts`.
 */

import { render, fireEvent } from '@testing-library/react';
import InfographicEditor from '@/components/editor';

beforeEach(() => {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getBoundingClientRect', {
    value: () => ({ left: 0, top: 0, width: 720, height: 720, right: 720, bottom: 720, x: 0, y: 0, toJSON: () => ({}) }),
    configurable: true,
  });
});

describe('Canvas click-to-select wiring', () => {
  test('renders two canvases (content + overlay)', () => {
    const { container } = render(<InfographicEditor />);
    const canvases = container.querySelectorAll('canvas');
    expect(canvases).toHaveLength(2);
  });

  test('overlay canvas has pointer-events: none', () => {
    const { container } = render(<InfographicEditor />);
    const canvases = container.querySelectorAll('canvas');
    const overlay = canvases[1] as HTMLCanvasElement;
    expect(overlay.style.pointerEvents).toBe('none');
  });

  test('overlay canvas is aria-hidden', () => {
    const { container } = render(<InfographicEditor />);
    const canvases = container.querySelectorAll('canvas');
    const overlay = canvases[1] as HTMLCanvasElement;
    expect(overlay.getAttribute('aria-hidden')).toBe('true');
  });

  test('mouseDown on empty canvas does not throw', () => {
    const { container } = render(<InfographicEditor />);
    const content = container.querySelectorAll('canvas')[0] as HTMLCanvasElement;
    expect(() => fireEvent.mouseDown(content, { clientX: 10, clientY: 10 })).not.toThrow();
  });

  test('mouseMove on canvas does not throw', () => {
    const { container } = render(<InfographicEditor />);
    const content = container.querySelectorAll('canvas')[0] as HTMLCanvasElement;
    expect(() => fireEvent.mouseMove(content, { clientX: 50, clientY: 50 })).not.toThrow();
  });

  test('mouseLeave on canvas does not throw', () => {
    const { container } = render(<InfographicEditor />);
    const content = container.querySelectorAll('canvas')[0] as HTMLCanvasElement;
    expect(() => fireEvent.mouseLeave(content)).not.toThrow();
  });

  test('click on empty canvas dispatches SELECT blockId: null — verified by checking LeftPanel state', () => {
    // Seed by clicking a LeftPanel block button to set selectedBlockId,
    // then click empty canvas area; the LeftPanel aria-pressed should flip.
    const { container, getAllByRole } = render(<InfographicEditor />);
    // Switch to Blocks tab
    const blocksTab = document.getElementById('left-tab-blocks');
    expect(blocksTab).toBeDefined();
    fireEvent.click(blocksTab!);

    const selectButtons = getAllByRole('button').filter(b => /^block\.select\.aria/i.test(b.getAttribute('aria-label') ?? ''));
    expect(selectButtons.length).toBeGreaterThan(0);
    fireEvent.click(selectButtons[0]);
    expect(selectButtons[0].getAttribute('aria-pressed')).toBe('true');

    // Click empty canvas — hit-test returns null (hitAreasRef is empty in
    // jsdom because getContext('2d') is null) → SELECT with null → deselect.
    const content = container.querySelectorAll('canvas')[0] as HTMLCanvasElement;
    fireEvent.mouseDown(content, { clientX: 10, clientY: 10 });

    expect(selectButtons[0].getAttribute('aria-pressed')).toBe('false');
  });
});

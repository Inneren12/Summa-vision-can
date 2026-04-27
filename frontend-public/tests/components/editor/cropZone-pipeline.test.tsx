/**
 * @jest-environment jsdom
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { TPLS, mkDoc } from '@/components/editor/registry/templates';

jest.mock('@/components/editor/renderer/overlay', () => {
  const actual = jest.requireActual('@/components/editor/renderer/overlay');
  return {
    ...actual,
    renderOverlay: jest.fn(actual.renderOverlay),
  };
});

jest.mock('@/components/editor/renderer/engine', () => {
  const actual = jest.requireActual('@/components/editor/renderer/engine');
  return {
    ...actual,
    renderDoc: jest.fn(() => []),
  };
});

jest.mock('@/components/editor/config/backgrounds', () => {
  const actual = jest.requireActual('@/components/editor/config/backgrounds');
  const noOp = { n: 'No-op', r: jest.fn() };
  return {
    ...actual,
    BGS: Object.keys(actual.BGS).reduce<Record<string, { n: string; r: jest.Mock }>>(
      (acc, key) => {
        acc[key] = noOp;
        return acc;
      },
      {},
    ),
  };
});

import InfographicEditor from '@/components/editor';
import { renderOverlay } from '@/components/editor/renderer/overlay';

const renderOverlayMock = renderOverlay as jest.MockedFunction<typeof renderOverlay>;

const baseDoc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
const initialDoc = {
  ...baseDoc,
  page: {
    ...baseDoc.page,
    size: 'instagram_1080' as const,
  },
};

describe('Crop-zone overlay pipeline', () => {
  beforeAll(() => {
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      writable: true,
      value: jest.fn(() => ({
        setTransform: jest.fn(),
        clearRect: jest.fn(),
        fillRect: jest.fn(),
        save: jest.fn(),
        restore: jest.fn(),
        beginPath: jest.fn(),
        moveTo: jest.fn(),
        lineTo: jest.fn(),
        quadraticCurveTo: jest.fn(),
        closePath: jest.fn(),
        fill: jest.fn(),
        strokeRect: jest.fn(),
        fillText: jest.fn(),
        measureText: jest.fn(() => ({ width: 40 })),
        setLineDash: jest.fn(),
      })),
    });
  });

  test('TopBar Crop toggle wires preset crop zone into renderOverlay payload', async () => {
    render(<InfographicEditor initialDoc={initialDoc} />);
    fireEvent.click(screen.getByRole('button', { name: 'editor.actions.cropZone' }));

    await waitFor(() => {
      expect(
        renderOverlayMock.mock.calls.some(([input]) =>
          Boolean(
            input.cropZone &&
              input.cropZone.platform === 'reddit' &&
              input.cropZone.x === 0 &&
              input.cropZone.y === 135 &&
              input.cropZone.w === 1080 &&
              input.cropZone.h === 810,
          ),
        ),
      ).toBe(true);
    });
  });
});

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TopBar } from '../TopBar';
import { initState } from '../../store/reducer';
import type { CompareResponse } from '@/lib/types/compare';

jest.mock('@/lib/api/admin', () => {
  const actual = jest.requireActual('@/lib/api/admin');
  return {
    ...actual,
    comparePublication: jest.fn(),
  };
});

import { comparePublication } from '@/lib/api/admin';

const mockedCompare = comparePublication as jest.MockedFunction<
  typeof comparePublication
>;

function makeProps(overrides: Partial<React.ComponentProps<typeof TopBar>> = {}) {
  const state = initState();
  const fileRef = React.createRef<HTMLInputElement>() as React.RefObject<
    HTMLInputElement | null
  >;
  return {
    doc: state.doc,
    dispatch: jest.fn(),
    undoStack: [],
    redoStack: [],
    dirty: false,
    mode: 'design' as const,
    setMode: jest.fn(),
    errs: 0,
    warns: 0,
    si: '0/0',
    canExp: true,
    fileRef,
    importJSON: jest.fn(),
    exportJSON: jest.fn(),
    markSaved: jest.fn(),
    exportZip: jest.fn(),
    zipExportPhase: null,
    saveStatus: 'idle' as const,
    fontsReady: true,
    publicationId: '42',
    ...overrides,
  };
}

describe('TopBar — compare integration (Phase 3.1d Slice 1b)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders Compare button initially with idle label', () => {
    render(<TopBar {...makeProps()} />);
    const btn = screen.getByTestId('compare-button');
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent('publication.compare.button.compare');
    expect(btn).not.toBeDisabled();
  });

  it('clicking Compare disables button and shows comparing label', async () => {
    mockedCompare.mockImplementation(() => new Promise(() => {}));
    render(<TopBar {...makeProps()} />);
    fireEvent.click(screen.getByTestId('compare-button'));
    await waitFor(() => {
      const btn = screen.getByTestId('compare-button');
      expect(btn).toHaveTextContent('publication.compare.button.comparing');
      expect(btn).toBeDisabled();
    });
  });

  it('after success with empty blocks falls through to overall_status', async () => {
    const result: CompareResponse = {
      publication_id: 42,
      overall_status: 'fresh',
      overall_severity: 'info',
      compared_at: new Date().toISOString(),
      block_results: [],
    };
    mockedCompare.mockResolvedValue(result);
    render(<TopBar {...makeProps()} />);
    fireEvent.click(screen.getByTestId('compare-button'));
    await waitFor(() => {
      const badge = screen.getByTestId('compare-badge');
      // Empty block_results falls through to overall_status: 'fresh'
      expect(badge).toHaveAttribute('data-severity', 'fresh');
    });
  });

  it('after partial result, retry button visible adjacent to badge', async () => {
    const result: CompareResponse = {
      publication_id: 42,
      overall_status: 'unknown',
      overall_severity: 'warning',
      compared_at: new Date().toISOString(),
      block_results: [
        {
          block_id: 'a',
          cube_id: 'c',
          semantic_key: 's',
          stale_status: 'unknown',
          stale_reasons: ['compare_failed'],
          severity: 'warning',
          compared_at: new Date().toISOString(),
          snapshot: null,
          current: null,
          compare_basis: {
            compare_kind: 'compare_failed',
            resolve_error: 'UNEXPECTED',
            details: { exception_type: 'X', message: 'm' },
          },
        },
      ],
    };
    mockedCompare.mockResolvedValue(result);
    render(<TopBar {...makeProps()} />);
    fireEvent.click(screen.getByTestId('compare-button'));
    await waitFor(() => {
      const badge = screen.getByTestId('compare-badge');
      expect(badge).toHaveAttribute('data-severity', 'partial');
      expect(screen.getByTestId('compare-retry')).toBeInTheDocument();
      expect(screen.getByTestId('compare-retry')).toHaveTextContent(
        'publication.compare.button.retry',
      );
    });
  });

  it('compare button disabled when no publicationId (template-only session)', () => {
    render(<TopBar {...makeProps({ publicationId: undefined })} />);
    expect(screen.getByTestId('compare-button')).toBeDisabled();
  });

  it('shows inline error label and retry when compare fails', async () => {
    mockedCompare.mockRejectedValue(new Error('Network down'));
    render(<TopBar {...makeProps()} />);
    fireEvent.click(screen.getByTestId('compare-button'));

    await waitFor(() => {
      expect(screen.getByTestId('compare-error')).toHaveTextContent(
        'publication.compare.error.label',
      );
      expect(screen.getByTestId('compare-error-retry')).toHaveTextContent(
        'publication.compare.error.retry',
      );
    });

    // Badge is NOT shown in error state
    expect(screen.queryByTestId('compare-badge')).not.toBeInTheDocument();
  });

  it('clicking error retry triggers a new compare', async () => {
    mockedCompare.mockRejectedValueOnce(new Error('First fail'));
    render(<TopBar {...makeProps()} />);
    fireEvent.click(screen.getByTestId('compare-button'));

    await waitFor(() => {
      expect(screen.getByTestId('compare-error-retry')).toBeInTheDocument();
    });

    mockedCompare.mockResolvedValueOnce({
      publication_id: 42,
      overall_status: 'fresh',
      overall_severity: 'info',
      compared_at: new Date().toISOString(),
      block_results: [],
    });

    fireEvent.click(screen.getByTestId('compare-error-retry'));

    await waitFor(() => {
      expect(screen.getByTestId('compare-badge')).toHaveAttribute(
        'data-severity',
        'fresh',
      );
    });
  });
});

/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock next/navigation
const mockGet = jest.fn();
jest.mock('next/navigation', () => ({
  useSearchParams: () => ({
    get: mockGet,
  }),
}));

// Track calls to getDownloadUrl to verify correct token is used
const mockGetDownloadUrl = jest.fn(
  (token: string) => `http://localhost:8000/api/v1/public/download?token=${token}`,
);
jest.mock('@/lib/api/client', () => ({
  getDownloadUrl: (...args: unknown[]) => mockGetDownloadUrl(...args as [string]),
}));

import DownloadingPage from '@/app/downloading/page';

describe('/downloading page', () => {
  let assignSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(window.history, 'replaceState').mockImplementation(() => {});

    // JSDOM does not support real navigation — spy on window.location.assign
    assignSpy = jest.spyOn(window.location, 'assign').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('shows error message when token is missing from URL', () => {
    mockGet.mockReturnValue(null);
    render(<DownloadingPage />);
    expect(screen.getByTestId('error-message')).toHaveTextContent(
      /invalid download link/i,
    );
  });

  it('shows "Verify and Download" button when token is present (no auto-download)', () => {
    mockGet.mockReturnValue('test-token-123');
    render(<DownloadingPage />);

    expect(screen.getByTestId('download-btn')).toBeInTheDocument();
    expect(screen.getByTestId('download-btn')).toHaveTextContent(
      /verify and download/i,
    );

    // CRITICAL: getDownloadUrl should NOT be called on mount (R17 — no auto-download)
    expect(mockGetDownloadUrl).not.toHaveBeenCalled();
  });

  it('clears token from URL on mount', () => {
    mockGet.mockReturnValue('test-token-123');
    render(<DownloadingPage />);

    expect(window.history.replaceState).toHaveBeenCalledWith(
      {},
      '',
      '/downloading',
    );
  });

  it('triggers download with correct token on button click', async () => {
    mockGet.mockReturnValue('test-token-123');
    render(<DownloadingPage />);

    const downloadBtn = screen.getByTestId('download-btn');
    await userEvent.click(downloadBtn);

    // Verify getDownloadUrl was called with the correct token
    expect(mockGetDownloadUrl).toHaveBeenCalledWith('test-token-123');
  });

  it('shows Summa Vision branding', () => {
    mockGet.mockReturnValue('test-token-123');
    render(<DownloadingPage />);
    expect(screen.getByText('Summa Vision')).toBeInTheDocument();
  });
});

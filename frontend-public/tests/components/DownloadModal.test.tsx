import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DownloadModal from '@/components/forms/DownloadModal';
import * as api from '@/lib/api/client';

jest.mock('@/lib/api/client');
jest.mock('@/components/forms/TurnstileWidget', () => {
  const React = require('react');
  return React.forwardRef(function MockTurnstile(
    props: { onSuccess: (token: string) => void; onError: () => void },
    _ref: React.Ref<unknown>,
  ) {
    return (
      <button
        data-testid="turnstile-widget"
        onClick={() => props.onSuccess('mock-turnstile-token')}
      >
        Mock Turnstile
      </button>
    );
  });
});

const mockCaptureLeadForDownload = api.captureLeadForDownload as jest.MockedFunction<
  typeof api.captureLeadForDownload
>;

describe('DownloadModal', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the trigger button', () => {
    render(<DownloadModal assetId={1} />);
    expect(screen.getByText('Download High-Res')).toBeInTheDocument();
  });

  it('opens modal on button click and shows Turnstile widget', async () => {
    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Get the High-Res Version')).toBeInTheDocument();
    expect(screen.getByTestId('turnstile-widget')).toBeInTheDocument();
  });

  it('renders email input', async () => {
    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    expect(screen.getByPlaceholderText('you@company.com')).toBeInTheDocument();
  });

  it('closes modal on × click', async () => {
    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    await userEvent.click(screen.getByLabelText('Close modal'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows validation error for empty email (Zod)', async () => {
    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));

    const submitBtn = screen.getByText('Get Download Link');
    await userEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('email-error')).toHaveTextContent(
      /email is required/i,
    );
  });

  it('shows error for invalid email format', async () => {
    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));

    await userEvent.type(screen.getByPlaceholderText('you@company.com'), 'notanemail');
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toBeInTheDocument();
    });
  });

  it('shows "Check your email" success state on successful submission', async () => {
    mockCaptureLeadForDownload.mockResolvedValue({
      message: 'Check your email for the download link',
    });

    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));

    // Complete Turnstile
    await userEvent.click(screen.getByTestId('turnstile-widget'));

    await userEvent.type(
      screen.getByPlaceholderText('you@company.com'),
      'user@company.ca',
    );
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByText('Check your email!')).toBeInTheDocument();
    });

    expect(screen.getByText(/user@company\.ca/)).toBeInTheDocument();
  });

  it('shows error for 403 (CAPTCHA failure)', async () => {
    mockCaptureLeadForDownload.mockRejectedValue(
      new Error('CAPTCHA verification failed'),
    );

    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    await userEvent.click(screen.getByTestId('turnstile-widget'));
    await userEvent.type(
      screen.getByPlaceholderText('you@company.com'),
      'user@company.ca',
    );
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByTestId('server-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('server-error')).toHaveTextContent(
      /verification failed/i,
    );
  });

  it('shows error for 429 (rate limited)', async () => {
    mockCaptureLeadForDownload.mockRejectedValue(
      new Error('Too many requests'),
    );

    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    await userEvent.click(screen.getByTestId('turnstile-widget'));
    await userEvent.type(
      screen.getByPlaceholderText('you@company.com'),
      'user@company.ca',
    );
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByTestId('server-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('server-error')).toHaveTextContent(
      /too many requests/i,
    );
  });

  it('shows error for 404 (asset not found)', async () => {
    mockCaptureLeadForDownload.mockRejectedValue(
      new Error('Asset not found or not yet published'),
    );

    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    await userEvent.click(screen.getByTestId('turnstile-widget'));
    await userEvent.type(
      screen.getByPlaceholderText('you@company.com'),
      'user@company.ca',
    );
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByTestId('server-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('server-error')).toHaveTextContent(
      /no longer available/i,
    );
  });

  it('does NOT auto-open URLs on success', async () => {
    mockCaptureLeadForDownload.mockResolvedValue({
      message: 'Check your email for the download link',
    });
    const openSpy = jest.spyOn(window, 'open');

    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    await userEvent.click(screen.getByTestId('turnstile-widget'));
    await userEvent.type(
      screen.getByPlaceholderText('you@company.com'),
      'user@company.ca',
    );
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByText('Check your email!')).toBeInTheDocument();
    });

    // No auto-open on success — download happens via Magic Link email
    expect(openSpy).not.toHaveBeenCalled();
    openSpy.mockRestore();
  });
});

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DownloadModal from '@/components/forms/DownloadModal';
import * as api from '@/lib/api/client';

jest.mock('@/lib/api/client');
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

  it('opens modal on button click', async () => {
    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Get the High-Res Version')).toBeInTheDocument();
  });

  it('closes modal on × click', async () => {
    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    await userEvent.click(screen.getByLabelText('Close modal'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows validation error for invalid email', async () => {
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

  it('shows error for obviously invalid email', async () => {
    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));

    await userEvent.type(screen.getByPlaceholderText('you@company.com'), 'notanemail');
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toBeInTheDocument();
    });
  });

  it('shows Download Now button on successful submission', async () => {
    mockCaptureLeadForDownload.mockResolvedValue({
      download_url: 'https://s3.example.com/presigned?token=abc',
      message: 'Check your email.',
    });

    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));

    await userEvent.type(
      screen.getByPlaceholderText('you@company.com'),
      'user@company.ca',
    );
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByTestId('download-now-btn')).toBeInTheDocument();
    });

    const downloadLink = screen.getByTestId('download-now-btn');
    expect(downloadLink).toHaveAttribute(
      'href',
      'https://s3.example.com/presigned?token=abc',
    );
    expect(downloadLink).toHaveAttribute('download');
  });

  it('does NOT auto-open the download URL in a new tab', async () => {
    mockCaptureLeadForDownload.mockResolvedValue({
      download_url: 'https://s3.example.com/url',
      message: 'ok',
    });
    const openSpy = jest.spyOn(window, 'open');

    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    await userEvent.type(
      screen.getByPlaceholderText('you@company.com'),
      'user@company.ca',
    );
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByTestId('download-now-btn')).toBeInTheDocument();
    });

    expect(openSpy).not.toHaveBeenCalled();
    openSpy.mockRestore();
  });

  it('shows server error message on API failure', async () => {
    mockCaptureLeadForDownload.mockRejectedValue(
      new Error('Too many requests'),
    );

    render(<DownloadModal assetId={1} />);
    await userEvent.click(screen.getByText('Download High-Res'));
    await userEvent.type(
      screen.getByPlaceholderText('you@company.com'),
      'user@company.ca',
    );
    await userEvent.click(screen.getByText('Get Download Link'));

    await waitFor(() => {
      expect(screen.getByTestId('server-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('server-error')).toHaveTextContent(
      'Too many requests',
    );
  });
});

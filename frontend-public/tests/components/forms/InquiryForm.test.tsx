import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InquiryForm from '@/components/forms/InquiryForm';

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('InquiryForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders all form fields', () => {
    render(<InquiryForm />);
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Company Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Budget')).toBeInTheDocument();
    expect(screen.getByLabelText('Message')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send Inquiry' })).toBeInTheDocument();
  });

  it('shows validation error for empty name on submit', async () => {
    render(<InquiryForm />);
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      expect(screen.getByTestId('name-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('name-error')).toHaveTextContent('Name is required');
  });

  it('rejects free email domain (gmail.com)', async () => {
    render(<InquiryForm />);

    await userEvent.type(screen.getByLabelText('Name'), 'Test User');
    await userEvent.type(screen.getByLabelText('Company Email'), 'test@gmail.com');
    await userEvent.selectOptions(screen.getByLabelText('Budget'), '$500–$1,000/month');
    await userEvent.type(
      screen.getByLabelText('Message'),
      'This is a test message with enough characters.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('email-error')).toHaveTextContent(
      'Please use your corporate email address',
    );
  });

  it('accepts ISP email domain (rogers.com) — backend handles scoring', async () => {
    render(<InquiryForm />);

    await userEvent.type(screen.getByLabelText('Company Email'), 'user@rogers.com');
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      // Other errors may appear (name, message) but NOT an email error
      expect(screen.queryByTestId('email-error')).not.toBeInTheDocument();
    });
  });

  it('accepts valid corporate email without showing email error', async () => {
    render(<InquiryForm />);

    await userEvent.type(screen.getByLabelText('Company Email'), 'ceo@tdbank.ca');
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      // Other errors may appear (name, message) but NOT an email error
      expect(screen.queryByTestId('email-error')).not.toBeInTheDocument();
    });
  });

  it('shows success state on successful submission', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ message: 'Inquiry received' }),
    });

    render(<InquiryForm />);

    await userEvent.type(screen.getByLabelText('Name'), 'Jane Doe');
    await userEvent.type(screen.getByLabelText('Company Email'), 'jane@bigcorp.ca');
    await userEvent.selectOptions(screen.getByLabelText('Budget'), '$1,000–$5,000/month');
    await userEvent.type(
      screen.getByLabelText('Message'),
      'We want to sponsor infographics about housing data in Canada.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      expect(screen.getByTestId('success-state')).toBeInTheDocument();
    });
    expect(screen.getByText("We'll be in touch within 24 hours.")).toBeInTheDocument();
  });

  it('shows backend detail message on 422', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({
        detail: 'Please use your corporate email address for sponsorship inquiries.',
      }),
    });

    render(<InquiryForm />);

    await userEvent.type(screen.getByLabelText('Name'), 'Jane Doe');
    await userEvent.type(screen.getByLabelText('Company Email'), 'jane@bigcorp.ca');
    await userEvent.selectOptions(screen.getByLabelText('Budget'), '$1,000–$5,000/month');
    await userEvent.type(
      screen.getByLabelText('Message'),
      'We want to sponsor infographics about housing data in Canada.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      expect(screen.getByTestId('server-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('server-error')).toHaveTextContent(
      'Please use your corporate email address for sponsorship inquiries.',
    );
  });

  it('shows generic fallback on 422 when detail is missing', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({}),
    });

    render(<InquiryForm />);

    await userEvent.type(screen.getByLabelText('Name'), 'Jane Doe');
    await userEvent.type(screen.getByLabelText('Company Email'), 'jane@bigcorp.ca');
    await userEvent.selectOptions(screen.getByLabelText('Budget'), '$1,000–$5,000/month');
    await userEvent.type(
      screen.getByLabelText('Message'),
      'We want to sponsor infographics about housing data in Canada.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      expect(screen.getByTestId('server-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('server-error')).toHaveTextContent(
      'Invalid submission. Please check your input.',
    );
  });

  it('shows rate limit error on 429', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Rate limit exceeded' }),
    });

    render(<InquiryForm />);

    await userEvent.type(screen.getByLabelText('Name'), 'Jane Doe');
    await userEvent.type(screen.getByLabelText('Company Email'), 'jane@bigcorp.ca');
    await userEvent.selectOptions(screen.getByLabelText('Budget'), '$1,000–$5,000/month');
    await userEvent.type(
      screen.getByLabelText('Message'),
      'We want to sponsor infographics about housing data in Canada.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      expect(screen.getByTestId('server-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('server-error')).toHaveTextContent(
      /recently submitted.*wait/i,
    );
  });

  it('shows network error on fetch failure', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    render(<InquiryForm />);

    await userEvent.type(screen.getByLabelText('Name'), 'Jane Doe');
    await userEvent.type(screen.getByLabelText('Company Email'), 'jane@bigcorp.ca');
    await userEvent.selectOptions(screen.getByLabelText('Budget'), '$1,000–$5,000/month');
    await userEvent.type(
      screen.getByLabelText('Message'),
      'We want to sponsor infographics about housing data in Canada.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Send Inquiry' }));

    await waitFor(() => {
      expect(screen.getByTestId('server-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('server-error')).toHaveTextContent(/network error/i);
  });
});

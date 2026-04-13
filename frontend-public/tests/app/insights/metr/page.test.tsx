import { render, screen } from '@testing-library/react';
import METRInsightPage from '@/app/insights/metr/page';

// Mock Next.js Link component
jest.mock('next/link', () => ({
  __esModule: true,
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe('METR Insight Page', () => {
  it('renders the headline text', () => {
    render(<METRInsightPage />);

    expect(screen.getByText('Working More Can Cost You')).toBeInTheDocument();
  });

  it('renders the poverty trap section', () => {
    render(<METRInsightPage />);

    expect(screen.getByText('The Poverty Trap')).toBeInTheDocument();
  });

  it('has a CTA link to /insights/metr/calculator', () => {
    render(<METRInsightPage />);

    const ctaLink = screen.getByTestId('calculator-cta');
    expect(ctaLink).toBeInTheDocument();
    expect(ctaLink).toHaveAttribute('href', '/insights/metr/calculator');
    expect(ctaLink).toHaveTextContent('Try the METR Calculator');
  });
});

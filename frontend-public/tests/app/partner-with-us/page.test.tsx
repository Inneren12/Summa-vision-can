import { render, screen } from '@testing-library/react';
import { SPONSORSHIP_TIERS, AUDIENCE_METRICS } from '@/lib/constants/pricing';
import PartnerPage from '@/app/partner-with-us/page';

// Mock the InquiryForm client component
jest.mock('@/components/forms/InquiryForm', () => {
  return function MockInquiryForm() {
    return <div data-testid="inquiry-form-mock">Inquiry Form</div>;
  };
});

describe('Partner Page', () => {
  it('renders 3 pricing tier cards', () => {
    render(<PartnerPage />);
    const tierCards = screen.getAllByTestId('tier-card');
    expect(tierCards).toHaveLength(3);
  });

  it('renders each tier name', () => {
    render(<PartnerPage />);
    expect(screen.getByText('Starter')).toBeInTheDocument();
    expect(screen.getByText('Growth')).toBeInTheDocument();
    expect(screen.getByText('Enterprise')).toBeInTheDocument();
  });

  it('renders tier prices from constants', () => {
    render(<PartnerPage />);
    expect(screen.getByText('$75 CPM')).toBeInTheDocument();
    expect(screen.getByText('$150 CPM')).toBeInTheDocument();
    expect(screen.getByText('Custom')).toBeInTheDocument();
  });

  it('renders "Most Popular" badge on the highlighted tier', () => {
    render(<PartnerPage />);
    // "Most Popular" appears as both the badge and the CTA button text
    const matches = screen.getAllByText('Most Popular');
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('renders audience metrics — monthly views', () => {
    render(<PartnerPage />);
    expect(screen.getByText('50,000+')).toBeInTheDocument();
  });

  it('renders audience metrics — engagement rate', () => {
    render(<PartnerPage />);
    expect(screen.getByText('4.2%')).toBeInTheDocument();
  });

  it('renders audience top subreddits', () => {
    render(<PartnerPage />);
    for (const sub of AUDIENCE_METRICS.topSubreddits) {
      expect(screen.getByText(sub)).toBeInTheDocument();
    }
  });

  it('renders audience platforms', () => {
    render(<PartnerPage />);
    for (const platform of AUDIENCE_METRICS.primaryPlatforms) {
      expect(screen.getByText(platform)).toBeInTheDocument();
    }
  });

  it('renders the inquiry form section', () => {
    render(<PartnerPage />);
    expect(screen.getByTestId('inquiry-form-mock')).toBeInTheDocument();
  });

  it('has CTA buttons linking to #inquiry', () => {
    render(<PartnerPage />);
    const ctaLinks = screen.getAllByRole('link');
    const inquiryLinks = ctaLinks.filter(
      (link) => link.getAttribute('href') === '#inquiry',
    );
    expect(inquiryLinks.length).toBe(3);
  });
});

describe('SPONSORSHIP_TIERS constant', () => {
  it('has exactly 3 tiers', () => {
    expect(SPONSORSHIP_TIERS).toHaveLength(3);
  });

  it('Growth tier (index 1) is highlighted', () => {
    expect(SPONSORSHIP_TIERS[1].highlighted).toBe(true);
  });

  it('Starter and Enterprise are not highlighted', () => {
    expect(SPONSORSHIP_TIERS[0].highlighted).toBe(false);
    expect(SPONSORSHIP_TIERS[2].highlighted).toBe(false);
  });

  it('each tier has required properties', () => {
    for (const tier of SPONSORSHIP_TIERS) {
      expect(tier.name).toBeTruthy();
      expect(tier.price).toBeTruthy();
      expect(tier.description).toBeTruthy();
      expect(tier.features.length).toBeGreaterThan(0);
      expect(tier.cta).toBeTruthy();
    }
  });
});

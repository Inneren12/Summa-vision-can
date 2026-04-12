import { render, screen } from '@testing-library/react';
import InfographicFeed from '@/components/gallery/InfographicFeed';
import { fetchPublishedGraphics } from '@/lib/api';

// Mock the API module
jest.mock('@/lib/api', () => ({
  fetchPublishedGraphics: jest.fn(),
}));

// Mock Next.js Image component
jest.mock('next/image', () => ({
  __esModule: true,
  default: ({ priority, fill, alt, ...props }: { priority?: boolean, fill?: boolean, alt: string, [key: string]: unknown }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img alt={alt} data-priority={priority ? "true" : undefined} data-fill={fill ? "true" : undefined} {...props} />;
  },
}));

// Mock Next.js Link component
jest.mock('next/link', () => ({
  __esModule: true,
  default: ({ children, href }: { children: React.ReactNode, href: string }) => {
    return <a href={href}>{children}</a>;
  },
}));

describe('InfographicFeed', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders image cards correctly when API returns data', async () => {
    const mockData = {
      items: [
        {
          id: 1,
          headline: 'Graphic 1',
          chart_type: 'bar',
          cdn_url: 'https://cdn.example.com/1.png',
          virality_score: 0.9,
          version: 1,
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 2,
          headline: 'Graphic 2',
          chart_type: 'line',
          cdn_url: 'https://cdn.example.com/2.png',
          virality_score: 0.5,
          version: 1,
          created_at: '2026-01-02T00:00:00Z',
        },
        {
          id: 3,
          headline: 'Graphic 3',
          chart_type: 'pie',
          cdn_url: 'https://cdn.example.com/3.png',
          virality_score: 0.75,
          version: 1,
          created_at: '2026-01-03T00:00:00Z',
        },
      ],
      total: 3,
      limit: 24,
      offset: 0,
    };

    (fetchPublishedGraphics as jest.Mock).mockResolvedValue(mockData);

    const ui = await InfographicFeed();
    render(ui);

    // Assert images
    expect(screen.getByAltText('Graphic 1')).toBeInTheDocument();
    expect(screen.getByAltText('Graphic 2')).toBeInTheDocument();
    expect(screen.getByAltText('Graphic 3')).toBeInTheDocument();

    // Assert headlines
    expect(screen.getByText('Graphic 1')).toBeInTheDocument();
    expect(screen.getByText('Graphic 2')).toBeInTheDocument();
    expect(screen.getByText('Graphic 3')).toBeInTheDocument();

    // Assert links to /graphics/{id}
    const links = screen.getAllByRole('link');
    expect(links.some(link => link.getAttribute('href') === '/graphics/1')).toBe(true);
    expect(links.some(link => link.getAttribute('href') === '/graphics/2')).toBe(true);
    expect(links.some(link => link.getAttribute('href') === '/graphics/3')).toBe(true);

    // Assert load more button is not present since offset < total is false
    expect(screen.queryByText('Load More')).not.toBeInTheDocument();
  });

  it('renders "coming soon" message when API returns 0 items', async () => {
    const mockData = { items: [], total: 0, limit: 24, offset: 0 };
    (fetchPublishedGraphics as jest.Mock).mockResolvedValue(mockData);

    const ui = await InfographicFeed();
    render(ui);

    expect(screen.getByText('New infographics coming soon. Check back later.')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    (fetchPublishedGraphics as jest.Mock).mockRejectedValue(new Error('Failed to fetch'));

    const ui = await InfographicFeed();
    render(ui);

    expect(screen.getByText('Could not load graphics. Please try again later.')).toBeInTheDocument();
    expect(screen.getByText('Try again')).toBeInTheDocument();
  });
});

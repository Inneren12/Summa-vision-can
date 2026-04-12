import { render, screen } from '@testing-library/react';
import GraphicPage, { generateMetadata } from '@/app/graphics/[id]/page';
import { fetchGraphic } from '@/lib/api';
import { notFound } from 'next/navigation';

// Mock the API and navigation modules
jest.mock('@/lib/api', () => ({
  fetchGraphic: jest.fn(),
}));

jest.mock('next/navigation', () => ({
  notFound: jest.fn(),
}));

// Mock DownloadModal component
jest.mock('@/components/forms/DownloadModal', () => ({
  __esModule: true,
  default: ({ assetId }: { assetId: number }) => (
    <div data-testid="download-modal">{assetId}</div>
  ),
}));

// Mock Next.js Image component
jest.mock('next/image', () => ({
  __esModule: true,
  default: ({ src, alt }: { src: string; alt: string }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} />;
  },
}));

describe('GraphicPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const mockGraphic = {
    id: 42,
    headline: 'Housing Starts 2026',
    chart_type: 'line',
    cdn_url: 'https://cdn.summa.vision/publications/42/v1/lowres.png',
    virality_score: 0.95,
    version: 1,
    created_at: '2026-04-01T00:00:00Z',
  };

  describe('generateMetadata', () => {
    it('returns correct metadata for an existing graphic', async () => {
      (fetchGraphic as jest.Mock).mockResolvedValue(mockGraphic);

      const params = Promise.resolve({ id: '42' });
      const metadata = await generateMetadata({ params });

      expect(metadata).toEqual({
        title: 'Housing Starts 2026 | Summa Vision',
        description: 'Canadian macro-economic data visualization: Housing Starts 2026',
        openGraph: {
          title: 'Housing Starts 2026',
          description: 'Canadian macro-economic data visualization: Housing Starts 2026',
          images: [
            {
              url: 'https://cdn.summa.vision/publications/42/v1/lowres.png',
              width: 1200,
              height: 630,
              alt: 'Housing Starts 2026',
            },
          ],
          type: 'article',
        },
        twitter: {
          card: 'summary_large_image',
          title: 'Housing Starts 2026',
          images: ['https://cdn.summa.vision/publications/42/v1/lowres.png'],
        },
      });
    });

    it('returns fallback metadata when API fails', async () => {
      (fetchGraphic as jest.Mock).mockRejectedValue(new Error('Not found'));

      const params = Promise.resolve({ id: '999' });
      const metadata = await generateMetadata({ params });

      expect(metadata).toEqual({
        title: 'Graphic Not Found | Summa Vision',
        description: 'The requested graphic could not be found.',
      });
    });
  });

  describe('Page Component', () => {
    it('renders the graphic successfully', async () => {
      (fetchGraphic as jest.Mock).mockResolvedValue(mockGraphic);

      const params = Promise.resolve({ id: '42' });
      const ui = await GraphicPage({ params });
      render(ui);

      expect(screen.getByText('Housing Starts 2026')).toBeInTheDocument();
      expect(screen.getByText('Version 1')).toBeInTheDocument();
      expect(screen.getByText('line')).toBeInTheDocument();
      expect(screen.getByAltText('Housing Starts 2026')).toHaveAttribute(
        'src',
        'https://cdn.summa.vision/publications/42/v1/lowres.png'
      );
      expect(screen.getByTestId('download-modal')).toHaveTextContent('42');
    });

    it('calls notFound when API fails', async () => {
      (fetchGraphic as jest.Mock).mockRejectedValue(new Error('Not found'));

      const params = Promise.resolve({ id: '999' });
      await GraphicPage({ params });

      expect(notFound).toHaveBeenCalled();
    });
  });
});

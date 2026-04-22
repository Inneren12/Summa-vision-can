import React from 'react';
import { render, screen } from '@testing-library/react';
import AdminIndexPage from '@/app/admin/page';
import { fetchAdminPublicationListServer } from '@/lib/api/admin-server';
import type { AdminPublicationResponse } from '@/lib/types/publication';

jest.mock('@/lib/api/admin-server', () => ({
  fetchAdminPublicationListServer: jest.fn(),
}));

const mockFetchList = fetchAdminPublicationListServer as jest.MockedFunction<
  typeof fetchAdminPublicationListServer
>;

function pub(overrides: Partial<AdminPublicationResponse> = {}): AdminPublicationResponse {
  return {
    id: '1',
    headline: 'Default Headline',
    chart_type: 'infographic',
    status: 'DRAFT',
    created_at: '2026-04-19T00:00:00Z',
    ...overrides,
  };
}

describe('AdminIndexPage', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders empty state when no publications', async () => {
    mockFetchList.mockResolvedValue([]);
    const ui = await AdminIndexPage();
    render(ui);
    expect(screen.getByText("publications.empty")).toBeInTheDocument();
  });

  it('renders a card for each publication with link to the editor', async () => {
    mockFetchList.mockResolvedValue([
      pub({ id: '1', headline: 'First Publication', status: 'DRAFT' }),
      pub({ id: '2', headline: 'Second Publication', status: 'PUBLISHED' }),
    ]);
    const ui = await AdminIndexPage();
    render(ui);

    expect(screen.getByText('First Publication')).toBeInTheDocument();
    expect(screen.getByText('Second Publication')).toBeInTheDocument();

    const links = screen.getAllByRole('link');
    const hrefs = links.map((l) => l.getAttribute('href'));
    expect(hrefs).toContain('/admin/editor/1');
    expect(hrefs).toContain('/admin/editor/2');
  });

  it('renders eyebrow and virality_score when present', async () => {
    mockFetchList.mockResolvedValue([
      pub({
        id: '1',
        headline: 'H',
        eyebrow: 'STATCAN',
        virality_score: 0.8,
      }),
    ]);
    const ui = await AdminIndexPage();
    render(ui);
    expect(screen.getByText('STATCAN')).toBeInTheDocument();
    expect(screen.getByText(/V:0\.8/)).toBeInTheDocument();
  });
});

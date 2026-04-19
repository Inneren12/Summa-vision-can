import React from 'react';
import { render } from '@testing-library/react';
import AdminEditorPage from '@/app/admin/editor/[id]/page';
import { fetchAdminPublicationServer } from '@/lib/api/admin-server';
import { notFound } from 'next/navigation';
import type { AdminPublicationResponse } from '@/lib/types/publication';

jest.mock('@/lib/api/admin-server', () => ({
  fetchAdminPublicationServer: jest.fn(),
}));

jest.mock('next/navigation', () => ({
  notFound: jest.fn(() => {
    throw new Error('NEXT_NOT_FOUND');
  }),
}));

// Mock the editor client so the test doesn't have to mount the full
// editor tree (canvas + every subcomponent). Assert prop wiring only.
jest.mock('@/app/admin/editor/[id]/AdminEditorClient', () => ({
  __esModule: true,
  default: (props: { publicationId: string; initialDoc: unknown }) => (
    <div
      data-testid="admin-editor-client"
      data-publication-id={props.publicationId}
      data-has-initial-doc={props.initialDoc != null ? 'yes' : 'no'}
    />
  ),
}));

const mockFetchOne = fetchAdminPublicationServer as jest.MockedFunction<
  typeof fetchAdminPublicationServer
>;
const mockNotFound = notFound as jest.MockedFunction<typeof notFound>;

function makePub(): AdminPublicationResponse {
  return {
    id: '42',
    headline: 'Test',
    chart_type: 'infographic',
    status: 'DRAFT',
    created_at: '2026-04-19T00:00:00Z',
  };
}

describe('AdminEditorPage', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders AdminEditorClient with publicationId and initialDoc on success', async () => {
    mockFetchOne.mockResolvedValue(makePub());
    const ui = await AdminEditorPage({ params: Promise.resolve({ id: '42' }) });
    const { getByTestId } = render(ui as React.ReactElement);

    const el = getByTestId('admin-editor-client');
    expect(el.getAttribute('data-publication-id')).toBe('42');
    expect(el.getAttribute('data-has-initial-doc')).toBe('yes');
  });

  it('calls notFound() when publication is missing', async () => {
    mockFetchOne.mockResolvedValue(null);
    await expect(
      AdminEditorPage({ params: Promise.resolve({ id: 'does-not-exist' }) }),
    ).rejects.toThrow('NEXT_NOT_FOUND');
    expect(mockNotFound).toHaveBeenCalled();
  });
});

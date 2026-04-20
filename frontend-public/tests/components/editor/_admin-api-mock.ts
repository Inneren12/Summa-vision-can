// Shared module-level mock for `@/lib/api/admin`. Importing this file
// hoists the `jest.mock` call so the editor's `updateAdminPublication`
// calls route to `mockUpdateAdminPublication` — a jest.fn() whose
// resolution behaviour each test case can control (resolve, reject,
// reject with AdminPublicationNotFoundError, etc.).
//
// Stage 4 Task 2 autosave tests are the first editor-suite consumers of
// a module-level admin-API mock. Earlier tests (save-snapshot,
// error-channels) exercised the reducer directly and did not need this.

import type { AdminPublicationResponse } from '@/lib/types/publication';

export const mockUpdateAdminPublication = jest.fn<
  Promise<AdminPublicationResponse>,
  [string, unknown]
>();

export class MockAdminPublicationNotFoundError extends Error {
  constructor(public readonly id: string) {
    super(`Publication ${id} not found`);
    this.name = 'AdminPublicationNotFoundError';
  }
}

jest.mock('@/lib/api/admin', () => ({
  __esModule: true,
  updateAdminPublication: mockUpdateAdminPublication,
  AdminPublicationNotFoundError: MockAdminPublicationNotFoundError,
}));

export function resetAdminApiMock(): void {
  mockUpdateAdminPublication.mockReset();
}

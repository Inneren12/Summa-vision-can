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
import { AdminPublicationNotFoundError as RealAdminPublicationNotFoundError } from '@/lib/api/admin';

export const mockUpdateAdminPublication = jest.fn<
  Promise<AdminPublicationResponse>,
  [string, unknown]
>();

export class MockAdminPublicationNotFoundError extends RealAdminPublicationNotFoundError {}

jest.mock('@/lib/api/admin', () => {
  // Spread the real module so new exports (error classes, etc.)
  // are available automatically without having to update this mock
  // every time something is added to admin.ts. We override ONLY the
  // HTTP function, because that's the only thing tests actually need
  // to control.
  const actual = jest.requireActual('@/lib/api/admin');
  return {
    __esModule: true,
    ...actual,
    updateAdminPublication: (...args: [string, unknown]) => mockUpdateAdminPublication(...args),
  };
});

export function resetAdminApiMock(): void {
  mockUpdateAdminPublication.mockReset();
}

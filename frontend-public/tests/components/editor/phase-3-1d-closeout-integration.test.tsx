/**
 * @jest-environment jsdom
 */

/**
 * Phase 3.1d Closeout (PR-09 / Slice 6) — integration coverage.
 *
 * Mounts the real <InfographicEditor /> with `@/lib/api/admin` mocked
 * (publishAdminPublication, comparePublication, fetchAdminPublication)
 * to exercise the full Slice 4a / 4b / 5 lifecycle end-to-end:
 *
 *   1. Happy publish: etagRef refresh → compare auto-trigger → MARK_PUBLISHED
 *   2. 412 conflict: PreconditionFailedModal with body_publish copy + Reload
 *   3. Pre-3.1d CTA: empty block_results + bindable doc → CTA → publish flow
 *   4. Reasons tooltip: parametrized over all 7 StaleReason enum values
 *
 * Test strategy locked by founder 2026-05-09: real editor mount with
 * mocked admin module. Playwright e2e harness deferred to Phase 4
 * per DEBT-080 (this PR).
 */

import React from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import enMessages from '@/../messages/en.json';
import type { Binding } from '@/components/editor/binding/types';
import type { CanonicalDocument, Block } from '@/components/editor/types';
import type {
  CompareResponse,
  StaleReason,
} from '@/lib/types/compare';
import { mkDoc, TPLS } from '@/components/editor/registry/templates';

type Messages = Record<string, unknown>;

// ─── i18n inlining (mirrors autosave-412-real-wire pattern) ────────────────

jest.mock('next-intl', () => {
  const ReactLib = jest.requireActual('react') as typeof React;
  type Msgs = Record<string, unknown>;
  const Ctx = ReactLib.createContext<{ messages: Msgs }>({ messages: {} });

  function get(messages: Msgs, path: string[]): unknown {
    return path.reduce<unknown>(
      (acc, key) => (acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[key] : undefined),
      messages,
    );
  }

  function useTranslations(namespace?: string) {
    const { messages } = ReactLib.useContext(Ctx);
    return (key: string, params?: Record<string, unknown>) => {
      const explode = (value: string) => value.split('.');
      const path = namespace ? [...explode(namespace), ...explode(key)] : explode(key);
      const val = get(messages, path);
      if (typeof val !== 'string') {
        return namespace ? `${namespace}.${key}` : key;
      }
      if (!params) return val;
      return Object.entries(params).reduce(
        (acc, [k, v]) => acc.replace(`{${k}}`, String(v)),
        val,
      );
    };
  }

  function NextIntlClientProvider({
    children,
    messages,
  }: {
    children: React.ReactNode;
    locale: string;
    messages: Record<string, unknown>;
  }) {
    return ReactLib.createElement(Ctx.Provider, { value: { messages } }, children);
  }

  return {
    useTranslations,
    useLocale: () => 'en',
    useFormatter: () => null,
    NextIntlClientProvider,
  };
});

// ─── Admin API mocks (publish + compare + fetch) ────────────────────────────

jest.mock('@/lib/api/admin', () => {
  const actual = jest.requireActual('@/lib/api/admin');
  return {
    ...actual,
    publishAdminPublication: jest.fn(),
    comparePublication: jest.fn(),
    fetchAdminPublication: jest.fn(),
  };
});

// next/navigation router stub (Editor calls useRouter)
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
  }),
}));

import { NextIntlClientProvider } from 'next-intl';
import InfographicEditor from '@/components/editor';
import {
  publishAdminPublication,
  comparePublication,
  fetchAdminPublication,
  BackendApiError,
} from '@/lib/api/admin';

const publishMock = publishAdminPublication as jest.MockedFunction<typeof publishAdminPublication>;
const compareMock = comparePublication as jest.MockedFunction<typeof comparePublication>;
const fetchMock = fetchAdminPublication as jest.MockedFunction<typeof fetchAdminPublication>;

// ─── Fixtures ───────────────────────────────────────────────────────────────

const SINGLE_BINDING: Binding = {
  kind: 'single',
  cube_id: '18100004',
  semantic_key: 'metric_x',
  filters: { '1': '12' },
  period: '2024-Q3',
};

function makeBindableDoc(): CanonicalDocument {
  // Start from the real single_stat_hero template so all required block
  // props are normalized correctly, then attach a binding to the
  // hero_stat block (v1 single-bindable allowlist) and force the
  // workflow into `exported` so the MARK_PUBLISHED transition button
  // is visible in the Review panel.
  const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
  const heroStatId = Object.values(doc.blocks).find(
    (b: Block) => b.type === 'hero_stat',
  )!.id;
  doc.blocks[heroStatId] = {
    ...doc.blocks[heroStatId],
    binding: SINGLE_BINDING,
  };
  doc.review.workflow = 'exported';
  return doc;
}

function makeEditorialDoc(): CanonicalDocument {
  // No hero_stat / delta_badge bindable blocks — single_stat_minimal has
  // hero_stat but we strip its binding to ensure the doc is not v1-bindable.
  const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
  for (const blockId of Object.keys(doc.blocks)) {
    delete doc.blocks[blockId].binding;
  }
  doc.review.workflow = 'exported';
  return doc;
}

function makeCompareResponse(opts: {
  block_results?: CompareResponse['block_results'];
  overall_status?: CompareResponse['overall_status'];
  overall_severity?: CompareResponse['overall_severity'];
} = {}): CompareResponse {
  return {
    publication_id: 1,
    overall_status: opts.overall_status ?? 'fresh',
    overall_severity: opts.overall_severity ?? 'info',
    compared_at: '2026-05-09T00:00:00Z',
    block_results: opts.block_results ?? [],
  };
}

interface RenderEditorOpts {
  publicationId?: string;
  initialEtag?: string;
  initialDoc?: CanonicalDocument;
}

function renderEditor(opts: RenderEditorOpts = {}) {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages as Messages}>
      <InfographicEditor
        publicationId={opts.publicationId ?? 'pub1'}
        initialEtag={opts.initialEtag ?? '"etag-initial"'}
        initialDoc={opts.initialDoc ?? makeBindableDoc()}
      />
    </NextIntlClientProvider>,
  );
}

function openReviewTab(): void {
  // RightRail review tab: role="tab", text from i18n key editor.right_rail.tab.review.
  // Click any tab whose accessible name matches /review/i.
  const reviewTab = screen
    .getAllByRole('tab')
    .find((el) => /review/i.test(el.textContent ?? ''));
  if (!reviewTab) {
    throw new Error('Review tab not found');
  }
  fireEvent.click(reviewTab);
}

// ─── Scenario 1 — Happy publish flow ────────────────────────────────────────

describe('PR-09 Scenario 1 — Happy publish flow (Slice 4b sequencing end-to-end)', () => {
  beforeEach(() => {
    publishMock.mockReset();
    compareMock.mockReset();
    fetchMock.mockReset();
  });

  it('publish 200 → onPublishSuccess refreshes etagRef → compare fired → MARK_PUBLISHED dispatched', async () => {
    publishMock.mockResolvedValueOnce({
      etag: '"etag-after-publish"',
      document: {} as never,
    });
    compareMock.mockResolvedValueOnce(
      makeCompareResponse({
        overall_status: 'fresh',
        block_results: [
          {
            block_id: 'b1',
            cube_id: 'c1',
            semantic_key: 's1',
            stale_status: 'fresh',
            stale_reasons: [],
            severity: 'info',
            compared_at: '2026-05-09T00:00:00Z',
            snapshot: null,
            current: null,
            compare_basis: { compare_kind: 'drift_check', matched_fields: [], drift_fields: [] },
          },
        ],
      }),
    );

    renderEditor();
    openReviewTab();

    const transitionBtn = await screen.findByTestId('transition-MARK_PUBLISHED');
    fireEvent.click(transitionBtn);

    const publishConfirm = await screen.findByTestId('publish-confirm-modal');
    expect(publishConfirm).toBeInTheDocument();

    const confirmBtn = within(publishConfirm).getByTestId('publish-modal-confirm');
    await act(async () => {
      fireEvent.click(confirmBtn);
    });

    // publish was called with the initial etag forwarded as If-Match
    expect(publishMock).toHaveBeenCalledWith(
      'pub1',
      expect.objectContaining({ bound_blocks: expect.any(Array) }),
      expect.objectContaining({ ifMatch: '"etag-initial"' }),
    );

    // compare auto-fired after publish success
    await waitFor(() => {
      expect(compareMock).toHaveBeenCalledWith('pub1', expect.any(Object));
    });

    // PublishConfirmModal closed (publish completed cleanly)
    await waitFor(() => {
      expect(screen.queryByTestId('publish-confirm-modal')).toBeNull();
    });
  });
});

// ─── Scenario 2 — 412 conflict full flow ────────────────────────────────────

describe('PR-09 Scenario 2 — 412 publish conflict flow', () => {
  beforeEach(() => {
    publishMock.mockReset();
    compareMock.mockReset();
    fetchMock.mockReset();
  });

  it('publish 412 → PreconditionFailedModal opens with body_publish copy; compare not fired', async () => {
    publishMock.mockRejectedValueOnce(
      new BackendApiError({
        status: 412,
        code: 'PRECONDITION_FAILED',
        message: 'stale',
        details: { server_etag: '"etag-server-current"', client_etag: '"etag-initial"' },
      }),
    );

    renderEditor();
    openReviewTab();

    fireEvent.click(await screen.findByTestId('transition-MARK_PUBLISHED'));
    const publishConfirm = await screen.findByTestId('publish-confirm-modal');
    await act(async () => {
      fireEvent.click(within(publishConfirm).getByTestId('publish-modal-confirm'));
    });

    // PreconditionFailedModal renders the publish-specific body copy
    const bodyText = enMessages.errors.backend.precondition_failed.body_publish;
    await waitFor(() => {
      expect(screen.getByText(bodyText)).toBeInTheDocument();
    });

    // compare did NOT auto-fire on the 412 branch
    expect(compareMock).not.toHaveBeenCalled();

    // server_etag from the 412 details surfaces on the dialog (dev-only attribute)
    const dialog = screen.getByRole('dialog');
    expect(dialog.getAttribute('data-server-etag')).toBe('"etag-server-current"');
  });

  it('Reload on 412 modal re-fetches publication and updates etagRef for the next publish', async () => {
    publishMock.mockRejectedValueOnce(
      new BackendApiError({
        status: 412,
        code: 'PRECONDITION_FAILED',
        message: 'stale',
        details: { server_etag: '"etag-server-current"' },
      }),
    );

    const freshDoc = makeBindableDoc();
    fetchMock.mockResolvedValueOnce({
      etag: '"etag-server-current"',
      id: 1,
      document_state: JSON.stringify(freshDoc),
    } as never);

    renderEditor();
    openReviewTab();

    fireEvent.click(await screen.findByTestId('transition-MARK_PUBLISHED'));
    const publishConfirm = await screen.findByTestId('publish-confirm-modal');
    await act(async () => {
      fireEvent.click(within(publishConfirm).getByTestId('publish-modal-confirm'));
    });

    const reloadBtn = await screen.findByRole('button', {
      name: /Reload \(lose my changes\)/i,
    });

    await act(async () => {
      fireEvent.click(reloadBtn);
    });

    expect(fetchMock).toHaveBeenCalledWith('pub1');

    // Subsequent publish attempt must carry the freshly-fetched etag.
    publishMock.mockResolvedValueOnce({
      etag: '"etag-after-second-publish"',
      document: {} as never,
    });
    compareMock.mockResolvedValueOnce(makeCompareResponse());

    // Re-open Review tab (IMPORT may have re-rendered tablist) and click MARK_PUBLISHED again.
    openReviewTab();
    fireEvent.click(await screen.findByTestId('transition-MARK_PUBLISHED'));
    const publishConfirm2 = await screen.findByTestId('publish-confirm-modal');
    await act(async () => {
      fireEvent.click(within(publishConfirm2).getByTestId('publish-modal-confirm'));
    });

    await waitFor(() => {
      expect(publishMock).toHaveBeenLastCalledWith(
        'pub1',
        expect.any(Object),
        expect.objectContaining({ ifMatch: '"etag-server-current"' }),
      );
    });
  });
});

// ─── Scenario 3 — Pre-3.1d CTA flow ─────────────────────────────────────────

describe('PR-09 Scenario 3 — Pre-3.1d Republish CTA flow', () => {
  beforeEach(() => {
    publishMock.mockReset();
    compareMock.mockReset();
    fetchMock.mockReset();
  });

  it('empty block_results + bindable doc → CTA renders → click opens publish modal', async () => {
    compareMock.mockResolvedValueOnce(
      makeCompareResponse({ overall_status: 'unknown', block_results: [] }),
    );

    renderEditor();

    fireEvent.click(screen.getByTestId('compare-button'));

    await waitFor(() => {
      expect(screen.getByTestId('republish-cta')).toBeInTheDocument();
    });

    publishMock.mockResolvedValueOnce({
      etag: '"etag-after-republish"',
      document: {} as never,
    });
    compareMock.mockResolvedValueOnce(
      makeCompareResponse({
        block_results: [
          {
            block_id: 'b1',
            cube_id: 'c1',
            semantic_key: 's1',
            stale_status: 'fresh',
            stale_reasons: [],
            severity: 'info',
            compared_at: '2026-05-09T00:00:00Z',
            snapshot: null,
            current: null,
            compare_basis: { compare_kind: 'drift_check', matched_fields: [], drift_fields: [] },
          },
        ],
      }),
    );

    fireEvent.click(screen.getByTestId('republish-cta'));

    const publishConfirm = await screen.findByTestId('publish-confirm-modal');
    expect(publishConfirm).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(within(publishConfirm).getByTestId('publish-modal-confirm'));
    });

    await waitFor(() => {
      expect(publishMock).toHaveBeenCalled();
    });
  });

  it('CTA NOT rendered when doc has no v1 bindable blocks (editorial-only)', async () => {
    compareMock.mockResolvedValueOnce(
      makeCompareResponse({ overall_status: 'unknown', block_results: [] }),
    );

    renderEditor({ initialDoc: makeEditorialDoc() });

    fireEvent.click(screen.getByTestId('compare-button'));

    await waitFor(() => {
      expect(screen.getByTestId('compare-badge')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('republish-cta')).toBeNull();
  });
});

// ─── Scenario 4 — Reasons tooltip i18n coverage (all 7 reasons) ─────────────

describe('PR-09 Scenario 4 — Reasons tooltip i18n coverage', () => {
  const ALL_REASONS: StaleReason[] = [
    'mapping_version_changed',
    'source_hash_changed',
    'value_changed',
    'missing_state_changed',
    'cache_row_stale',
    'compare_failed',
    'snapshot_missing',
  ];

  const EXPECTED_LABELS: Record<StaleReason, string> = {
    mapping_version_changed: 'Semantic mapping changed',
    source_hash_changed: 'Source data changed',
    value_changed: 'Value changed',
    missing_state_changed: 'Data availability changed',
    cache_row_stale: 'Cached data is stale',
    compare_failed: 'Comparison failed',
    snapshot_missing: 'No snapshot to compare against',
  };

  beforeEach(() => {
    publishMock.mockReset();
    compareMock.mockReset();
    fetchMock.mockReset();
  });

  it.each(ALL_REASONS)('renders i18n label for reason: %s', async (reason) => {
    const compare_basis =
      reason === 'compare_failed'
        ? {
            compare_kind: 'compare_failed' as const,
            resolve_error: 'UNEXPECTED' as const,
            details: { exception_type: 'X', message: 'y' },
          }
        : reason === 'snapshot_missing'
          ? { compare_kind: 'snapshot_missing' as const, cause: 'no_snapshot_row' as const }
          : {
              compare_kind: 'drift_check' as const,
              matched_fields: [],
              drift_fields: [],
            };

    compareMock.mockResolvedValueOnce(
      makeCompareResponse({
        overall_status: 'stale',
        overall_severity: 'warning',
        block_results: [
          {
            block_id: 'b1',
            cube_id: 'c1',
            semantic_key: 's1',
            stale_status: 'stale',
            stale_reasons: [reason],
            severity: 'warning',
            compared_at: '2026-05-09T00:00:00Z',
            snapshot: null,
            current: null,
            compare_basis,
          },
        ],
      }),
    );

    renderEditor();

    fireEvent.click(screen.getByTestId('compare-button'));

    const wrapper = await screen.findByTestId('compare-badge-wrapper');
    fireEvent.mouseEnter(wrapper);

    const tooltip = await screen.findByTestId('compare-reasons-tooltip');
    expect(within(tooltip).getByText(EXPECTED_LABELS[reason])).toBeInTheDocument();
  });
});

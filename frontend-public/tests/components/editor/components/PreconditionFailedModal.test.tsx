/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PreconditionFailedModal } from '@/components/editor/components/PreconditionFailedModal';

// Minimal next-intl shim: returns the dotted key path verbatim so assertions
// can match on stable, locale-agnostic strings.
jest.mock('next-intl', () => ({
  useTranslations: (namespace?: string) => (key: string) =>
    namespace ? `${namespace}.${key}` : key,
}));

function renderModal(
  overrides: Partial<React.ComponentProps<typeof PreconditionFailedModal>> = {},
) {
  const onReload = jest.fn();
  const onSaveAsNewDraft = jest.fn();
  const onDismiss = jest.fn();
  const utils = render(
    <PreconditionFailedModal
      open
      serverEtag={'"abc1234567890"'}
      onReload={onReload}
      onSaveAsNewDraft={onSaveAsNewDraft}
      onDismiss={onDismiss}
      {...overrides}
    />,
  );
  return { ...utils, onReload, onSaveAsNewDraft, onDismiss };
}

describe('PreconditionFailedModal', () => {
  test('renders nothing when open is false', () => {
    const { queryByRole } = renderModal({ open: false });
    expect(queryByRole('dialog')).toBeNull();
  });

  test('renders title, body, and both buttons; Reload becomes default focus', async () => {
    renderModal();
    expect(
      screen.getByText('errors.backend.precondition_failed.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('errors.backend.precondition_failed.body'),
    ).toBeInTheDocument();
    const reloadButton = screen.getByRole('button', {
      name: 'errors.backend.precondition_failed.button_reload',
    });
    expect(reloadButton).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: 'errors.backend.precondition_failed.button_save_as_draft',
      }),
    ).toBeInTheDocument();
    // queueMicrotask focus assignment runs on the next microtask tick.
    await Promise.resolve();
    await Promise.resolve();
    expect(document.activeElement).toBe(reloadButton);
  });

  test('Reload click invokes onReload', async () => {
    const { onReload, onSaveAsNewDraft } = renderModal();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole('button', {
        name: 'errors.backend.precondition_failed.button_reload',
      }),
    );
    expect(onReload).toHaveBeenCalledTimes(1);
    expect(onSaveAsNewDraft).not.toHaveBeenCalled();
  });

  test('Save-as-draft click invokes onSaveAsNewDraft', async () => {
    const { onReload, onSaveAsNewDraft } = renderModal();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole('button', {
        name: 'errors.backend.precondition_failed.button_save_as_draft',
      }),
    );
    expect(onSaveAsNewDraft).toHaveBeenCalledTimes(1);
    expect(onReload).not.toHaveBeenCalled();
  });

  test('Esc key invokes onDismiss but NOT onReload or onSaveAsNewDraft', async () => {
    const { onReload, onSaveAsNewDraft, onDismiss } = renderModal();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(onReload).not.toHaveBeenCalled();
    expect(onSaveAsNewDraft).not.toHaveBeenCalled();
  });

  test('exposes serverEtag via data attribute outside production builds', () => {
    // Jest sets NODE_ENV='test', so the dev/test-only attribute is present here.
    // The complementary production-build assertion lives in the next test.
    renderModal({ serverEtag: '"feedface"' });
    const dialog = screen.getByRole('dialog');
    expect(dialog.getAttribute('data-server-etag')).toBe('"feedface"');
  });

  test('does not expose serverEtag data attribute in production builds', () => {
    // Phase 1.3 polish: in production the concurrency token must not surface
    // in the DOM. The component's spread-conditional renders the attribute
    // only when NODE_ENV !== 'production'.
    const previous = process.env.NODE_ENV;
    // Object.defineProperty avoids tripping CRA/Jest read-only NODE_ENV
    // guards in some environments.
    Object.defineProperty(process.env, 'NODE_ENV', {
      value: 'production',
      configurable: true,
    });
    try {
      renderModal({ serverEtag: '"feedface"' });
      const dialog = screen.getByRole('dialog');
      expect(dialog.hasAttribute('data-server-etag')).toBe(false);
    } finally {
      Object.defineProperty(process.env, 'NODE_ENV', {
        value: previous,
        configurable: true,
      });
    }
  });
});

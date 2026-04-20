/**
 * @jest-environment jsdom
 *
 * Unit tests for `SaveStatusIndicator` (Stage 4 Task 2). Renders the
 * component in isolation to confirm the four-state resolution table
 * matches the design.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SaveStatusIndicator } from '@/components/editor/components/SaveStatusIndicator';

describe('SaveStatusIndicator', () => {
  test('renders nothing when clean and idle', () => {
    const { container } = render(
      <SaveStatusIndicator dirty={false} saveStatus="idle" />,
    );
    expect(container.firstChild).toBeNull();
  });

  test('dirty + idle → amber dot, aria "Unsaved changes", data-status=unsaved', () => {
    render(<SaveStatusIndicator dirty={true} saveStatus="idle" />);
    const indicator = screen.getByTestId('save-status-indicator');
    expect(indicator).toHaveAttribute('aria-label', 'Unsaved changes');
    expect(indicator).toHaveAttribute('data-status', 'unsaved');
  });

  test('dirty + pending → amber dot, aria "Unsaved changes", data-status=pending', () => {
    render(<SaveStatusIndicator dirty={true} saveStatus="pending" />);
    const indicator = screen.getByTestId('save-status-indicator');
    expect(indicator).toHaveAttribute('aria-label', 'Unsaved changes');
    expect(indicator).toHaveAttribute('data-status', 'pending');
  });

  test('saving → amber pulse, aria "Saving", data-status=saving', () => {
    render(<SaveStatusIndicator dirty={true} saveStatus="saving" />);
    const indicator = screen.getByTestId('save-status-indicator');
    expect(indicator).toHaveAttribute('aria-label', 'Saving');
    expect(indicator).toHaveAttribute('data-status', 'saving');
  });

  test('error → red dot, aria "Save failed", data-status=error', () => {
    render(<SaveStatusIndicator dirty={true} saveStatus="error" />);
    const indicator = screen.getByTestId('save-status-indicator');
    expect(indicator).toHaveAttribute('aria-label', 'Save failed');
    expect(indicator).toHaveAttribute('data-status', 'error');
  });

  test('error outranks dirty=false', () => {
    // If a save failed then the user dismissed, status should still be
    // respected — though in practice DISMISS_SAVE_ERROR clears the error
    // channel before the effect resets status. This guards the display
    // table directly: error status wins regardless of dirty.
    render(<SaveStatusIndicator dirty={false} saveStatus="error" />);
    const indicator = screen.getByTestId('save-status-indicator');
    expect(indicator).toHaveAttribute('data-status', 'error');
  });
});

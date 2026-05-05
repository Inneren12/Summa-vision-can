import React from 'react';
import { render, screen } from '@testing-library/react';
import { CompareBadge } from '../CompareBadge';

/**
 * Tests assert on `namespace.key` form because the project-wide next-intl
 * mock (`src/__mocks__/next-intl/index.ts`) returns the dotted key name as
 * the translated string. Locale-correctness is verified by the i18n
 * catalog-coverage tests, not here.
 */
describe('CompareBadge', () => {
  it('renders fresh severity with check glyph and label key', () => {
    render(<CompareBadge severity="fresh" />);
    const badge = screen.getByTestId('compare-badge');
    expect(badge).toHaveAttribute('data-severity', 'fresh');
    expect(badge).toHaveTextContent('✓');
    expect(badge).toHaveTextContent('publication.compare.badge.fresh');
  });

  it('renders stale severity with warning glyph', () => {
    render(<CompareBadge severity="stale" />);
    const badge = screen.getByTestId('compare-badge');
    expect(badge).toHaveAttribute('data-severity', 'stale');
    expect(badge).toHaveTextContent('⚠');
    expect(badge).toHaveTextContent('publication.compare.badge.stale');
  });

  it('renders missing severity with × glyph', () => {
    render(<CompareBadge severity="missing" />);
    const badge = screen.getByTestId('compare-badge');
    expect(badge).toHaveAttribute('data-severity', 'missing');
    expect(badge).toHaveTextContent('×');
    expect(badge).toHaveTextContent('publication.compare.badge.missing');
  });

  it('renders partial severity with ◐ glyph', () => {
    render(<CompareBadge severity="partial" />);
    const badge = screen.getByTestId('compare-badge');
    expect(badge).toHaveAttribute('data-severity', 'partial');
    expect(badge).toHaveTextContent('◐');
    expect(badge).toHaveTextContent('publication.compare.badge.partial');
  });

  it('renders not_compared placeholder when no compare run yet', () => {
    render(<CompareBadge severity="not_compared" />);
    const badge = screen.getByTestId('compare-badge');
    expect(badge).toHaveAttribute('data-severity', 'not_compared');
    expect(badge).toHaveTextContent('publication.compare.badge.not_compared');
  });

  it('renders unknown severity with ? glyph', () => {
    render(<CompareBadge severity="unknown" />);
    const badge = screen.getByTestId('compare-badge');
    expect(badge).toHaveAttribute('data-severity', 'unknown');
    expect(badge).toHaveTextContent('?');
    expect(badge).toHaveTextContent('publication.compare.badge.unknown');
  });
});

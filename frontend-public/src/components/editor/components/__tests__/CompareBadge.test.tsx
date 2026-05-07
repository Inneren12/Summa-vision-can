import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
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

describe('CompareBadge — Slice 5 reasons tooltip', () => {
  it('does NOT render tooltip when reasons array is empty', () => {
    render(<CompareBadge severity="fresh" reasons={[]} />);
    fireEvent.mouseEnter(screen.getByTestId('compare-badge-wrapper'));
    expect(screen.queryByTestId('compare-reasons-tooltip')).toBeNull();
  });

  it('does NOT render tooltip when reasons is undefined (back-compat)', () => {
    render(<CompareBadge severity="fresh" />);
    fireEvent.mouseEnter(screen.getByTestId('compare-badge-wrapper'));
    expect(screen.queryByTestId('compare-reasons-tooltip')).toBeNull();
  });

  it('reveals tooltip on mouseEnter, hides on mouseLeave', () => {
    render(<CompareBadge severity="stale" reasons={['value_changed']} />);
    const wrapper = screen.getByTestId('compare-badge-wrapper');
    expect(screen.queryByTestId('compare-reasons-tooltip')).toBeNull();
    fireEvent.mouseEnter(wrapper);
    expect(screen.getByTestId('compare-reasons-tooltip')).toBeInTheDocument();
    fireEvent.mouseLeave(wrapper);
    expect(screen.queryByTestId('compare-reasons-tooltip')).toBeNull();
  });

  it('reveals tooltip on focus (keyboard accessibility)', () => {
    render(<CompareBadge severity="stale" reasons={['value_changed']} />);
    const wrapper = screen.getByTestId('compare-badge-wrapper');
    fireEvent.focus(wrapper);
    expect(screen.getByTestId('compare-reasons-tooltip')).toBeInTheDocument();
    fireEvent.blur(wrapper);
    expect(screen.queryByTestId('compare-reasons-tooltip')).toBeNull();
  });

  it('makes wrapper tab-stoppable only when reasons are present', () => {
    const { rerender } = render(<CompareBadge severity="fresh" />);
    expect(screen.getByTestId('compare-badge-wrapper')).toHaveAttribute('tabindex', '-1');
    rerender(<CompareBadge severity="stale" reasons={['value_changed']} />);
    expect(screen.getByTestId('compare-badge-wrapper')).toHaveAttribute('tabindex', '0');
  });

  it('renders one <li> per reason in input order', () => {
    render(
      <CompareBadge
        severity="stale"
        reasons={['value_changed', 'cache_row_stale', 'snapshot_missing']}
      />,
    );
    fireEvent.mouseEnter(screen.getByTestId('compare-badge-wrapper'));
    const tooltip = screen.getByTestId('compare-reasons-tooltip');
    expect(tooltip.querySelectorAll('li').length).toBe(3);
  });

  it('does NOT dedupe input — caller (aggregateReasons) is responsible (PR-08 R2 contract)', () => {
    // Defensive dedup in the component would mask upstream bugs.
    // aggregateReasons is the documented dedup point.
    const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <CompareBadge
        severity="stale"
        reasons={['value_changed', 'value_changed']}
      />,
    );
    fireEvent.mouseEnter(screen.getByTestId('compare-badge-wrapper'));
    const tooltip = screen.getByTestId('compare-reasons-tooltip');
    expect(tooltip.querySelectorAll('li').length).toBe(2);
    errSpy.mockRestore();
  });

  it('exposes ARIA describedby linkage when tooltip is visible', () => {
    render(<CompareBadge severity="stale" reasons={['value_changed']} />);
    const wrapper = screen.getByTestId('compare-badge-wrapper');
    expect(wrapper).not.toHaveAttribute('aria-describedby');
    fireEvent.mouseEnter(wrapper);
    const id = wrapper.getAttribute('aria-describedby');
    expect(id).toBeTruthy();
    expect(screen.getByTestId('compare-reasons-tooltip')).toHaveAttribute('id', id ?? '');
  });
});

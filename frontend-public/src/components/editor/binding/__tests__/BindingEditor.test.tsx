import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import type { Block } from '../../types';
import type { SingleValueBinding } from '../types';

jest.mock('@/lib/api/admin-discovery', () => ({
  searchCubes: jest.fn(),
  listSemanticMappings: jest.fn(),
  getCubeMetadata: jest.fn(),
  DiscoveryFetchError: class extends Error {},
}));

jest.mock('../ResolvePreview', () => ({
  ResolvePreview: ({ binding }: { binding: unknown }) =>
    binding ? <div data-testid="mock-resolve-preview">mock</div> : null,
}));

import {
  searchCubes,
  listSemanticMappings,
  getCubeMetadata,
} from '@/lib/api/admin-discovery';
import { BindingEditor } from '../BindingEditor';

const mockSearchCubes = searchCubes as jest.MockedFunction<typeof searchCubes>;
const mockListSemanticMappings = listSemanticMappings as jest.MockedFunction<typeof listSemanticMappings>;
const mockGetCubeMetadata = getCubeMetadata as jest.MockedFunction<typeof getCubeMetadata>;

function makeBlock(overrides: Partial<Block> = {}): Block {
  return {
    id: 'blk_1',
    type: 'hero_stat',
    props: { value: '6.73%', label: '5-year fixed rate' },
    visible: true,
    ...overrides,
  };
}

function neverResolves<T>(): Promise<T> {
  return new Promise(() => {});
}

beforeEach(() => {
  jest.useFakeTimers();
  mockSearchCubes.mockReset();
  mockListSemanticMappings.mockReset();
  mockGetCubeMetadata.mockReset();
});

afterEach(() => {
  act(() => {
    jest.runOnlyPendingTimers();
  });
  jest.useRealTimers();
});

describe('BindingEditor — render', () => {
  it('renders for hero_stat block (no advisory)', () => {
    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    expect(screen.getByTestId('binding-editor')).toBeInTheDocument();
    expect(screen.queryByTestId('binding-editor-delta-advisory')).toBeNull();
  });

  it('renders advisory note for delta_badge block', () => {
    render(
      <BindingEditor
        block={makeBlock({ type: 'delta_badge', props: { value: '+2pp', direction: 'positive' } })}
        onChange={jest.fn()}
      />,
    );
    const advisory = screen.getByTestId('binding-editor-delta-advisory');
    expect(advisory).toHaveTextContent('Frontend does not compute deltas');
  });

  it('semantic_key dropdown is disabled until a cube is selected', () => {
    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    expect(screen.getByTestId('binding-editor-semantic-key')).toBeDisabled();
  });
});

describe('BindingEditor — initial state from block.binding', () => {
  it('seeds form fields when binding kind is single', () => {
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'metric_x',
      filters: { geo: 'CA' },
      period: '2024-Q3',
      format: 'percent',
    };
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());
    render(<BindingEditor block={makeBlock({ binding })} onChange={jest.fn()} />);
    expect((screen.getByTestId('binding-editor-period') as HTMLInputElement).value).toBe('2024-Q3');
    expect((screen.getByTestId('binding-editor-format') as HTMLInputElement).value).toBe('percent');
    expect(screen.getByTestId('binding-editor-selected-cube')).toHaveTextContent('18100004');
  });

  it('renders empty fields when block.binding is undefined', () => {
    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    expect((screen.getByTestId('binding-editor-period') as HTMLInputElement).value).toBe('');
    expect(screen.queryByTestId('binding-editor-selected-cube')).toBeNull();
  });

  it('treats non-single binding kind as no initial state', () => {
    const binding = {
      kind: 'time_series',
      cube_id: 'c',
      semantic_key: 'k',
      filters: {},
      period_range: { last_n: 4 },
    } as unknown as SingleValueBinding;
    render(<BindingEditor block={makeBlock({ binding })} onChange={jest.fn()} />);
    expect((screen.getByTestId('binding-editor-period') as HTMLInputElement).value).toBe('');
  });
});

describe('BindingEditor — onChange contract', () => {
  it('does NOT emit on mount with empty form (touched gate)', () => {
    const onChange = jest.fn();
    render(<BindingEditor block={makeBlock()} onChange={onChange} />);
    // Pre-fix this test asserted onChange(undefined); under the touched
    // gate (Phase 3.1d Slice 3a fix), no emit until user interacts.
    expect(onChange).not.toHaveBeenCalled();
  });

  // (Removed: pre-fix test "emits canonical Binding when all fields are valid"
  //  asserted mount-time emit, which the touched gate now blocks. Equivalent
  //  user-interaction-driven assertion lives in the touched-gate describe.)

  it('emits undefined when period is cleared', () => {
    const onChange = jest.fn();
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'metric_x',
      filters: { geo: 'CA' },
      period: '2024-Q3',
    };
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());
    render(<BindingEditor block={makeBlock({ binding })} onChange={onChange} />);
    onChange.mockClear();
    fireEvent.change(screen.getByTestId('binding-editor-period'), { target: { value: '' } });
    expect(onChange).toHaveBeenLastCalledWith(undefined);
  });
});

describe('BindingEditor — cube search', () => {
  it('debounces search and calls searchCubes', async () => {
    mockSearchCubes.mockResolvedValue([
      {
        product_id: '18100004',
        cube_id_statcan: 18100004,
        title_en: 'Posted rates',
        subject_en: 'Finance',
        frequency: 'M',
      },
    ]);
    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    fireEvent.change(screen.getByLabelText('Cube search'), { target: { value: 'rate' } });
    expect(mockSearchCubes).not.toHaveBeenCalled();
    await act(async () => {
      jest.advanceTimersByTime(260);
    });
    expect(mockSearchCubes).toHaveBeenCalledTimes(1);
    expect(mockSearchCubes).toHaveBeenCalledWith(
      expect.objectContaining({ q: 'rate' }),
    );
  });

  it('does not call searchCubes when query is empty', async () => {
    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    fireEvent.change(screen.getByLabelText('Cube search'), { target: { value: '   ' } });
    await act(async () => {
      jest.advanceTimersByTime(260);
    });
    // Trim is applied — whitespace-only is treated as empty.
    fireEvent.change(screen.getByLabelText('Cube search'), { target: { value: '' } });
    expect(mockSearchCubes).not.toHaveBeenCalled();
  });

  it('aborts in-flight request on rapid keystroke', async () => {
    let firstSignal: AbortSignal | undefined;
    mockSearchCubes.mockImplementationOnce((opts) => {
      firstSignal = opts.signal;
      return neverResolves();
    });
    mockSearchCubes.mockResolvedValueOnce([]);

    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    fireEvent.change(screen.getByLabelText('Cube search'), { target: { value: 'a' } });
    await act(async () => {
      jest.advanceTimersByTime(260);
    });
    expect(firstSignal?.aborted).toBe(false);

    fireEvent.change(screen.getByLabelText('Cube search'), { target: { value: 'ab' } });
    await act(async () => {
      jest.advanceTimersByTime(260);
    });
    expect(firstSignal?.aborted).toBe(true);
  });

  it('selecting a cube populates cubeId and triggers metadata loads', async () => {
    mockSearchCubes.mockResolvedValue([
      {
        product_id: '18100004',
        cube_id_statcan: 18100004,
        title_en: 'Posted rates',
        subject_en: 'Finance',
        frequency: 'M',
      },
    ]);
    mockListSemanticMappings.mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
    });
    mockGetCubeMetadata.mockResolvedValue({
      cube_id: '18100004',
      product_id: 18100004,
      dimensions: [],
      frequency_code: 'M',
      cube_title_en: null,
      cube_title_fr: null,
    });

    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    fireEvent.change(screen.getByLabelText('Cube search'), { target: { value: 'rate' } });
    await act(async () => {
      jest.advanceTimersByTime(260);
    });
    await waitFor(() => screen.getByTestId('binding-editor-cube-results'));
    fireEvent.click(screen.getByText('Posted rates'));

    await waitFor(() => {
      expect(mockListSemanticMappings).toHaveBeenCalledWith(
        expect.objectContaining({ cube_id: '18100004', limit: 100 }),
      );
      expect(mockGetCubeMetadata).toHaveBeenCalledWith('18100004', expect.anything());
    });
    expect(screen.getByTestId('binding-editor-selected-cube')).toHaveTextContent('18100004');
  });
});

describe('BindingEditor — semantic mappings + cube metadata', () => {
  beforeEach(() => {
    mockListSemanticMappings.mockResolvedValue({
      items: [
        {
          id: 1,
          cube_id: '18100004',
          product_id: 18100004,
          semantic_key: 'rate_5yr_fixed',
          label: '5-year fixed',
          description: null,
          config: {},
          is_active: true,
          version: 1,
          created_at: '',
          updated_at: '',
          updated_by: null,
        },
        {
          id: 2,
          cube_id: '18100004',
          product_id: 18100004,
          semantic_key: 'rate_5yr_fixed_change_pct',
          label: '5-year fixed Δ%',
          description: null,
          config: {},
          is_active: true,
          version: 1,
          created_at: '',
          updated_at: '',
          updated_by: null,
        },
      ],
      total: 2,
      limit: 100,
      offset: 0,
    });
    mockGetCubeMetadata.mockResolvedValue({
      cube_id: '18100004',
      product_id: 18100004,
      dimensions: [
        {
          position_id: 1,
          name_en: 'Geography',
          name_fr: 'Géographie',
          has_uom: false,
          members: [
            { member_id: 1, name_en: 'Canada', name_fr: 'Canada' },
            { member_id: 2, name_en: 'Ontario', name_fr: 'Ontario' },
          ],
        },
      ],
      frequency_code: 'M',
      cube_title_en: null,
      cube_title_fr: null,
    });
  });

  it('populates semantic_key dropdown after cube selected (delta_badge sees ALL keys, not pre-filtered)', async () => {
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: '',
      filters: { '1': '1' },
      period: '2024-Q3',
    };
    render(
      <BindingEditor
        block={makeBlock({
          type: 'delta_badge',
          props: { value: '', direction: 'neutral' },
          binding,
        })}
        onChange={jest.fn()}
      />,
    );
    await waitFor(() => {
      const sel = screen.getByTestId('binding-editor-semantic-key') as HTMLSelectElement;
      expect(sel.options.length).toBe(3); // placeholder + 2 keys (no client filter)
    });
    const sel = screen.getByTestId('binding-editor-semantic-key') as HTMLSelectElement;
    const values = Array.from(sel.options).map((o) => o.value);
    expect(values).toEqual(
      expect.arrayContaining(['rate_5yr_fixed', 'rate_5yr_fixed_change_pct']),
    );
  });

  it('renders dim/member selectors once metadata loads', async () => {
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'rate_5yr_fixed',
      filters: { '1': '1' },
      period: '2024-Q3',
    };
    render(<BindingEditor block={makeBlock({ binding })} onChange={jest.fn()} />);
    await waitFor(() => screen.getByTestId('binding-editor-filter-1'));
    const filter = screen.getByTestId('binding-editor-filter-1') as HTMLSelectElement;
    expect(filter.options.length).toBe(3); // placeholder + 2 members
    expect((filter as HTMLSelectElement).value).toBe('1');
  });

  it('selecting a member updates filters and re-emits binding', async () => {
    const onChange = jest.fn();
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'rate_5yr_fixed',
      filters: { '1': '1' },
      period: '2024-Q3',
    };
    render(<BindingEditor block={makeBlock({ binding })} onChange={onChange} />);
    await waitFor(() => screen.getByTestId('binding-editor-filter-1'));
    onChange.mockClear();
    fireEvent.change(screen.getByTestId('binding-editor-filter-1'), {
      target: { value: '2' },
    });
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        kind: 'single',
        filters: { '1': '2' },
      }),
    );
  });
});

describe('BindingEditor — touched gate (Phase 3.1d Slice 3a fix)', () => {
  it('does NOT call onChange on mount when block has an existing valid binding', () => {
    const onChange = jest.fn();
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'metric_x',
      filters: { geo: 'CA' },
      period: '2024-Q3',
    };
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());
    render(<BindingEditor block={makeBlock({ binding })} onChange={onChange} />);
    // No interaction → no emit.
    expect(onChange).not.toHaveBeenCalled();
  });

  it('does NOT call onChange on mount when block has no binding', () => {
    const onChange = jest.fn();
    render(<BindingEditor block={makeBlock()} onChange={onChange} />);
    // touched=false, so the emit useEffect short-circuits.
    expect(onChange).not.toHaveBeenCalled();
  });

  it('emits canonical binding when user touches a field after mount with existing binding', () => {
    const onChange = jest.fn();
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'metric_x',
      filters: { geo: 'CA' },
      period: '2024-Q3',
    };
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());
    render(<BindingEditor block={makeBlock({ binding })} onChange={onChange} />);
    fireEvent.change(screen.getByTestId('binding-editor-period'), {
      target: { value: '2024-Q4' },
    });
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ kind: 'single', period: '2024-Q4' }),
    );
  });

  it('emits undefined when user clears a required field (user-initiated invalid)', () => {
    const onChange = jest.fn();
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'metric_x',
      filters: { geo: 'CA' },
      period: '2024-Q3',
    };
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());
    render(<BindingEditor block={makeBlock({ binding })} onChange={onChange} />);
    fireEvent.change(screen.getByTestId('binding-editor-period'), {
      target: { value: '' },
    });
    expect(onChange).toHaveBeenLastCalledWith(undefined);
  });
});

describe('BindingEditor — block.id sync (Phase 3.1d Slice 3a fix)', () => {
  it('resets form state when inspector switches to a different bindable block', () => {
    const onChange = jest.fn();
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());

    const blockA = makeBlock({
      id: 'blk_a',
      type: 'hero_stat',
      binding: {
        kind: 'single',
        cube_id: '18100004',
        semantic_key: 'metric_a',
        filters: { geo: 'CA' },
        period: '2024-Q1',
      },
    });
    const blockB = makeBlock({
      id: 'blk_b',
      type: 'delta_badge',
      props: { value: '+1pp', direction: 'positive' },
      binding: {
        kind: 'single',
        cube_id: '36100434',
        semantic_key: 'metric_b',
        filters: { geo: 'ON' },
        period: '2024-Q3',
      },
    });

    const { rerender } = render(<BindingEditor block={blockA} onChange={onChange} />);
    expect(screen.getByTestId('binding-editor-selected-cube')).toHaveTextContent('18100004');

    onChange.mockClear();
    rerender(<BindingEditor block={blockB} onChange={onChange} />);
    expect(screen.getByTestId('binding-editor-selected-cube')).toHaveTextContent('36100434');
    expect((screen.getByTestId('binding-editor-period') as HTMLInputElement).value).toBe('2024-Q3');
    // No emit on the rerender — touched is reset.
    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders empty form when switching to a block with no binding', () => {
    const onChange = jest.fn();
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());
    const blockA = makeBlock({
      id: 'blk_a',
      binding: {
        kind: 'single',
        cube_id: '18100004',
        semantic_key: 'metric_a',
        filters: { geo: 'CA' },
        period: '2024-Q1',
      },
    });
    const blockB = makeBlock({ id: 'blk_b' });
    const { rerender } = render(<BindingEditor block={blockA} onChange={onChange} />);
    rerender(<BindingEditor block={blockB} onChange={onChange} />);
    expect(screen.queryByTestId('binding-editor-selected-cube')).toBeNull();
    expect((screen.getByTestId('binding-editor-period') as HTMLInputElement).value).toBe('');
  });
});

describe('BindingEditor — cube change resets dependent fields (Phase 3.1d Slice 3a fix)', () => {
  it('selecting a new cube clears semanticKey and filters', async () => {
    const onChange = jest.fn();
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'rate_5yr_fixed',
      filters: { geo: 'CA' },
      period: '2024-Q3',
    };
    mockSearchCubes.mockResolvedValue([
      {
        product_id: '36100434',
        cube_id_statcan: 36100434,
        title_en: 'Different cube',
        subject_en: 'Other',
        frequency: 'A',
      },
    ]);
    mockListSemanticMappings.mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
    });
    mockGetCubeMetadata.mockResolvedValue({
      cube_id: '36100434',
      product_id: 36100434,
      dimensions: [],
      frequency_code: 'A',
      cube_title_en: null,
      cube_title_fr: null,
    });

    render(<BindingEditor block={makeBlock({ binding })} onChange={onChange} />);
    onChange.mockClear();

    fireEvent.change(screen.getByLabelText('Cube search'), { target: { value: 'diff' } });
    await act(async () => {
      jest.advanceTimersByTime(260);
    });
    await waitFor(() => screen.getByTestId('binding-editor-cube-results'));
    fireEvent.click(screen.getByText('Different cube'));

    // Cube changed → semanticKey + filters reset → emit undefined (semantic_key empty).
    await waitFor(() => {
      expect(onChange).toHaveBeenCalled();
    });
    expect(onChange).toHaveBeenLastCalledWith(undefined);
  });
});

describe('BindingEditor — ResolvePreview integration (Phase 3.1d Slice 3b)', () => {
  it('mounts ResolvePreview when block has valid single binding', () => {
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'metric_x',
      filters: { '1': '1' },
      period: '2024-Q3',
    };
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());
    render(<BindingEditor block={makeBlock({ binding })} onChange={jest.fn()} />);
    expect(screen.getByTestId('mock-resolve-preview')).toBeInTheDocument();
  });

  it('does not mount ResolvePreview when block has no binding', () => {
    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    expect(screen.queryByTestId('mock-resolve-preview')).toBeNull();
  });
});

describe('BindingEditor — Clear binding button (Phase 3.1d Slice 3a fix)', () => {
  it('Clear button is disabled when block has no binding', () => {
    render(<BindingEditor block={makeBlock()} onChange={jest.fn()} />);
    const btn = screen.getByTestId('binding-editor-clear') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('Clear button is enabled and emits undefined when block has a binding', () => {
    const onChange = jest.fn();
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'metric_x',
      filters: { geo: 'CA' },
      period: '2024-Q3',
    };
    mockListSemanticMappings.mockReturnValue(neverResolves());
    mockGetCubeMetadata.mockReturnValue(neverResolves());
    render(<BindingEditor block={makeBlock({ binding })} onChange={onChange} />);
    onChange.mockClear();
    const btn = screen.getByTestId('binding-editor-clear') as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
    fireEvent.click(btn);
    expect(onChange).toHaveBeenLastCalledWith(undefined);
  });
});

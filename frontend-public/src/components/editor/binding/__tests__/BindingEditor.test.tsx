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
  it('emits undefined for an empty / invalid form', () => {
    const onChange = jest.fn();
    render(<BindingEditor block={makeBlock()} onChange={onChange} />);
    expect(onChange).toHaveBeenLastCalledWith(undefined);
  });

  it('emits canonical Binding when all fields are valid', () => {
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
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        kind: 'single',
        cube_id: '18100004',
        semantic_key: 'metric_x',
        period: '2024-Q3',
      }),
    );
  });

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
      dimensions: {},
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
      dimensions: {
        geo: {
          label: 'Geography',
          members: [
            { id: 'CA', label: 'Canada' },
            { id: 'ON', label: 'Ontario' },
          ],
        },
      },
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
      filters: { geo: 'CA' },
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
      filters: { geo: 'CA' },
      period: '2024-Q3',
    };
    render(<BindingEditor block={makeBlock({ binding })} onChange={jest.fn()} />);
    await waitFor(() => screen.getByTestId('binding-editor-filter-geo'));
    const filter = screen.getByTestId('binding-editor-filter-geo') as HTMLSelectElement;
    expect(filter.options.length).toBe(3); // placeholder + 2 members
    expect((filter as HTMLSelectElement).value).toBe('CA');
  });

  it('selecting a member updates filters and re-emits binding', async () => {
    const onChange = jest.fn();
    const binding: SingleValueBinding = {
      kind: 'single',
      cube_id: '18100004',
      semantic_key: 'rate_5yr_fixed',
      filters: { geo: 'CA' },
      period: '2024-Q3',
    };
    render(<BindingEditor block={makeBlock({ binding })} onChange={onChange} />);
    await waitFor(() => screen.getByTestId('binding-editor-filter-geo'));
    onChange.mockClear();
    fireEvent.change(screen.getByTestId('binding-editor-filter-geo'), {
      target: { value: 'ON' },
    });
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        kind: 'single',
        filters: { geo: 'ON' },
      }),
    );
  });
});

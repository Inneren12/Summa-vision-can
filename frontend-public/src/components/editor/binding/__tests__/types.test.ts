import {
  validateBinding,
  type SingleValueBinding,
  type TimeSeriesBinding,
  type CategoricalSeriesBinding,
  type MultiMetricBinding,
  type TabularBinding,
} from '../types';

describe('validateBinding', () => {
  describe('valid bindings', () => {
    it('accepts SingleValueBinding without format', () => {
      const input: SingleValueBinding = {
        kind: 'single',
        cube_id: 'cube_a',
        semantic_key: 'metric_x',
        filters: { geo: 'ON' },
        period: '2024-Q3',
      };
      expect(validateBinding(input)).toEqual(input);
    });

    it('accepts SingleValueBinding with format', () => {
      const input: SingleValueBinding = {
        kind: 'single',
        cube_id: 'cube_a',
        semantic_key: 'metric_x',
        filters: { geo: 'ON' },
        period: '2024-Q3',
        format: 'currency',
      };
      expect(validateBinding(input)).toEqual(input);
    });

    it('accepts TimeSeriesBinding with from/to range', () => {
      const input: TimeSeriesBinding = {
        kind: 'time_series',
        cube_id: 'cube_a',
        semantic_key: 'metric_x',
        filters: { geo: 'ON' },
        period_range: { from: '2020-Q1', to: '2024-Q3' },
      };
      expect(validateBinding(input)).toEqual(input);
    });

    it('accepts TimeSeriesBinding with last_n range', () => {
      const input: TimeSeriesBinding = {
        kind: 'time_series',
        cube_id: 'cube_a',
        semantic_key: 'metric_x',
        filters: { geo: 'ON' },
        period_range: { last_n: 12 },
        series_dim: 'province',
      };
      expect(validateBinding(input)).toEqual(input);
    });

    it('accepts CategoricalSeriesBinding without sort/limit', () => {
      const input: CategoricalSeriesBinding = {
        kind: 'categorical_series',
        cube_id: 'cube_a',
        semantic_key: 'metric_x',
        category_dim: 'province',
        filters: { year: '2024' },
        period: '2024-Q3',
      };
      expect(validateBinding(input)).toEqual(input);
    });

    it('accepts CategoricalSeriesBinding with sort + limit', () => {
      const input: CategoricalSeriesBinding = {
        kind: 'categorical_series',
        cube_id: 'cube_a',
        semantic_key: 'metric_x',
        category_dim: 'province',
        filters: { year: '2024' },
        period: '2024-Q3',
        sort: 'value_desc',
        limit: 10,
      };
      expect(validateBinding(input)).toEqual(input);
    });

    it('accepts MultiMetricBinding', () => {
      const input: MultiMetricBinding = {
        kind: 'multi_metric',
        cube_id: 'cube_a',
        metrics: [
          { semantic_key: 'metric_a' },
          { semantic_key: 'metric_b', label: 'B' },
        ],
        filters: { geo: 'ON' },
        period: '2024-Q3',
      };
      expect(validateBinding(input)).toEqual(input);
    });

    it('accepts TabularBinding', () => {
      const input: TabularBinding = {
        kind: 'tabular',
        cube_id: 'cube_a',
        columns: [{ semantic_key: 'col_a', label: 'A' }, { semantic_key: 'col_b' }],
        row_dim: 'province',
        filters: { year: '2024' },
        period: '2024-Q3',
      };
      expect(validateBinding(input)).toEqual(input);
    });
  });

  describe('rejects malformed input', () => {
    it('returns null when kind is missing', () => {
      expect(
        validateBinding({
          cube_id: 'c',
          semantic_key: 'k',
          filters: {},
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('returns null for unknown kind discriminator (forward compat)', () => {
      expect(
        validateBinding({
          kind: 'future_kind',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('returns null when SingleValueBinding is missing cube_id', () => {
      expect(
        validateBinding({
          kind: 'single',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('returns null when cube_id is wrong type', () => {
      expect(
        validateBinding({
          kind: 'single',
          cube_id: 42,
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('returns null for null input', () => {
      expect(validateBinding(null)).toBeNull();
    });

    it('returns null for undefined input', () => {
      expect(validateBinding(undefined)).toBeNull();
    });

    it.each([['string'], [42], [[]]])(
      'returns null for non-object input (%p)',
      (val) => {
        expect(validateBinding(val)).toBeNull();
      },
    );

    it('returns null when filters values are not strings', () => {
      expect(
        validateBinding({
          kind: 'single',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: 42 },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('returns null for invalid sort enum', () => {
      expect(
        validateBinding({
          kind: 'categorical_series',
          cube_id: 'c',
          semantic_key: 'k',
          category_dim: 'province',
          filters: { year: '2024' },
          period: '2024-Q3',
          sort: 'alphabetical',
        }),
      ).toBeNull();
    });

    it('rejects empty cube_id', () => {
      expect(
        validateBinding({
          kind: 'single',
          cube_id: '',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('rejects empty period', () => {
      expect(
        validateBinding({
          kind: 'single',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period: '',
        }),
      ).toBeNull();
    });

    it('rejects empty semantic_key', () => {
      expect(
        validateBinding({
          kind: 'single',
          cube_id: 'c',
          semantic_key: '',
          filters: { geo: 'ON' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('rejects last_n: 0', () => {
      expect(
        validateBinding({
          kind: 'time_series',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period_range: { last_n: 0 },
        }),
      ).toBeNull();
    });

    it('rejects last_n: -1', () => {
      expect(
        validateBinding({
          kind: 'time_series',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period_range: { last_n: -1 },
        }),
      ).toBeNull();
    });

    it('rejects last_n: 1.5 (non-integer)', () => {
      expect(
        validateBinding({
          kind: 'time_series',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period_range: { last_n: 1.5 },
        }),
      ).toBeNull();
    });

    it('rejects last_n: NaN', () => {
      expect(
        validateBinding({
          kind: 'time_series',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period_range: { last_n: NaN },
        }),
      ).toBeNull();
    });

    it('rejects limit: 0', () => {
      expect(
        validateBinding({
          kind: 'categorical_series',
          cube_id: 'c',
          semantic_key: 'k',
          category_dim: 'province',
          filters: { year: '2024' },
          period: '2024-Q3',
          limit: 0,
        }),
      ).toBeNull();
    });

    it('rejects period_range with both from/to and last_n (mutex)', () => {
      expect(
        validateBinding({
          kind: 'time_series',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: 'ON' },
          period_range: { from: '2020-Q1', to: '2024-Q3', last_n: 12 },
        }),
      ).toBeNull();
    });

    it('rejects filter with empty member id', () => {
      expect(
        validateBinding({
          kind: 'single',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { geo: '' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('rejects filter with empty key', () => {
      expect(
        validateBinding({
          kind: 'single',
          cube_id: 'c',
          semantic_key: 'k',
          filters: { '': 'value' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('rejects empty metrics array', () => {
      expect(
        validateBinding({
          kind: 'multi_metric',
          cube_id: 'c',
          metrics: [],
          filters: { geo: 'ON' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });

    it('rejects empty columns array', () => {
      expect(
        validateBinding({
          kind: 'tabular',
          cube_id: 'c',
          columns: [],
          row_dim: 'province',
          filters: { year: '2024' },
          period: '2024-Q3',
        }),
      ).toBeNull();
    });
  });

  describe('canonical reconstruction', () => {
    it('strips unknown extra keys from valid input', () => {
      const input = {
        kind: 'single',
        cube_id: 'cube_a',
        semantic_key: 'metric_x',
        filters: { geo: 'ON' },
        period: '2024-Q3',
        extra_unknown_field: 'should be stripped',
      };
      const result = validateBinding(input);
      expect(result).not.toBeNull();
      expect(result).not.toHaveProperty('extra_unknown_field');
      expect(result).toEqual({
        kind: 'single',
        cube_id: 'cube_a',
        semantic_key: 'metric_x',
        filters: { geo: 'ON' },
        period: '2024-Q3',
      });
    });
  });
});

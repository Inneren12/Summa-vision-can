import { fetchMETRCalculation, fetchMETRCurve } from '@/lib/api/metr';
import type { METRCalculateResponse, METRCurveResponse } from '@/lib/types/metr';

// ---------------------------------------------------------------------------
// Mock global fetch
// ---------------------------------------------------------------------------

const originalFetch = global.fetch;

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
});

const mockFetch = () => global.fetch as jest.MockedFunction<typeof global.fetch>;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const sampleCalcResponse: METRCalculateResponse = {
  gross_income: 60000,
  net_income: 45000,
  metr: 48.2,
  zone: 'high',
  keep_per_dollar: 0.518,
  components: {
    federal_tax: 20.5,
    provincial_tax: 9.15,
    cpp: 5.95,
    cpp2: 0,
    ei: 1.58,
    ohp: 0,
    ccb: 7.3,
    gst_credit: 2.0,
    cwb: 1.2,
    provincial_benefits: 0.52,
  },
};

const sampleCurveResponse: METRCurveResponse = {
  province: 'BC',
  family_type: 'single_parent',
  n_children: 2,
  children_under_6: 1,
  curve: [
    { gross: 15000, net: 14200, metr: 22.0, zone: 'normal' },
    { gross: 30000, net: 25000, metr: 55.0, zone: 'high' },
    { gross: 50000, net: 38000, metr: 70.0, zone: 'dead_zone' },
  ],
  dead_zones: [{ start: 25000, end: 45000, peak_metr: 72.3 }],
  peak: { gross: 50000, metr: 70.0 },
  annotations: [{ gross: 50000, metr: 70.0, label: 'Earn $1 more. Keep 30¢.' }],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('fetchMETRCalculation', () => {
  it('sends correct query params in the URL', async () => {
    mockFetch().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleCalcResponse),
    } as Response);

    await fetchMETRCalculation({
      income: 60000,
      province: 'BC',
      family_type: 'single_parent',
      n_children: 2,
      children_under_6: 1,
    });

    const calledUrl = mockFetch().mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/public/metr/calculate?');
    expect(calledUrl).toContain('income=60000');
    expect(calledUrl).toContain('province=BC');
    expect(calledUrl).toContain('family_type=single_parent');
    expect(calledUrl).toContain('n_children=2');
    expect(calledUrl).toContain('children_under_6=1');
  });

  it('throws on non-OK response with detail message', async () => {
    mockFetch().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Rate limit exceeded' }),
    } as Response);

    await expect(
      fetchMETRCalculation({ income: 60000 }),
    ).rejects.toThrow('Rate limit exceeded');
  });

  it('throws fallback message when error body is not JSON', async () => {
    mockFetch().mockResolvedValue({
      ok: false,
      json: () => Promise.reject(new Error('parse error')),
    } as Response);

    await expect(
      fetchMETRCalculation({ income: 60000 }),
    ).rejects.toThrow('METR calculation failed');
  });
});

describe('fetchMETRCurve', () => {
  it('returns typed response with correct structure', async () => {
    mockFetch().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleCurveResponse),
    } as Response);

    const result = await fetchMETRCurve({
      province: 'BC',
      family_type: 'single_parent',
      n_children: 2,
    });

    // Verify the response matches the expected type structure
    expect(result.province).toBe('BC');
    expect(result.family_type).toBe('single_parent');
    expect(result.n_children).toBe(2);
    expect(result.curve).toHaveLength(3);
    expect(result.curve[0]).toEqual(
      expect.objectContaining({ gross: 15000, metr: 22.0, zone: 'normal' }),
    );
    expect(result.dead_zones).toHaveLength(1);
    expect(result.dead_zones[0].peak_metr).toBe(72.3);
    expect(result.peak.metr).toBe(70.0);
    expect(result.annotations).toHaveLength(1);
  });

  it('sends correct query params in the URL', async () => {
    mockFetch().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleCurveResponse),
    } as Response);

    await fetchMETRCurve({
      province: 'BC',
      family_type: 'single_parent',
      n_children: 2,
      income_min: 10000,
      income_max: 200000,
      step: 2000,
    });

    const calledUrl = mockFetch().mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/public/metr/curve?');
    expect(calledUrl).toContain('province=BC');
    expect(calledUrl).toContain('family_type=single_parent');
    expect(calledUrl).toContain('n_children=2');
    expect(calledUrl).toContain('income_min=10000');
    expect(calledUrl).toContain('income_max=200000');
    expect(calledUrl).toContain('step=2000');
  });

  it('calls URL without query string when no params provided', async () => {
    mockFetch().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleCurveResponse),
    } as Response);

    await fetchMETRCurve();

    const calledUrl = mockFetch().mock.calls[0][0] as string;
    expect(calledUrl).toMatch(/\/api\/v1\/public\/metr\/curve$/);
    expect(calledUrl).not.toContain('?');
  });

  it('throws on non-OK response', async () => {
    mockFetch().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Rate limit exceeded' }),
    } as Response);

    await expect(fetchMETRCurve({ province: 'ON' })).rejects.toThrow(
      'Rate limit exceeded',
    );
  });
});

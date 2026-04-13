import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import METRCalculator from '@/components/metr/METRCalculator';
import * as metrApi from '@/lib/api/metr';
import type { METRCalculateResponse, METRCurveResponse } from '@/lib/types/metr';

jest.mock('@/lib/api/metr');

const mockFetchMETRCalculation = metrApi.fetchMETRCalculation as jest.MockedFunction<
  typeof metrApi.fetchMETRCalculation
>;
const mockFetchMETRCurve = metrApi.fetchMETRCurve as jest.MockedFunction<
  typeof metrApi.fetchMETRCurve
>;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockCalcResponse: METRCalculateResponse = {
  gross_income: 50000,
  net_income: 39200,
  metr: 42.5,
  zone: 'normal',
  keep_per_dollar: 0.575,
  components: {
    federal_tax: 15.0,
    provincial_tax: 5.05,
    cpp: 5.95,
    cpp2: 0,
    ei: 1.58,
    ohp: 0,
    ccb: 10.2,
    gst_credit: 2.5,
    cwb: 1.5,
    provincial_benefits: 0.72,
  },
};

const mockCurveResponse: METRCurveResponse = {
  province: 'ON',
  family_type: 'single',
  n_children: 0,
  children_under_6: 0,
  curve: [
    { gross: 15000, net: 14500, metr: 20.0, zone: 'normal' },
    { gross: 25000, net: 22000, metr: 35.0, zone: 'normal' },
    { gross: 35000, net: 28500, metr: 55.0, zone: 'high' },
    { gross: 45000, net: 35000, metr: 65.0, zone: 'dead_zone' },
    { gross: 55000, net: 43500, metr: 40.0, zone: 'normal' },
  ],
  dead_zones: [],
  peak: { gross: 45000, metr: 65.0 },
  annotations: [
    { gross: 45000, metr: 65.0, label: 'Earn $1 more. Keep 35¢.' },
  ],
};

const mockCurveWithDeadZones: METRCurveResponse = {
  ...mockCurveResponse,
  dead_zones: [
    { start: 30000, end: 50000, peak_metr: 78.5 },
  ],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupDefaultMocks() {
  mockFetchMETRCalculation.mockResolvedValue(mockCalcResponse);
  mockFetchMETRCurve.mockResolvedValue(mockCurveResponse);
}

function setupDeadZoneMocks() {
  mockFetchMETRCalculation.mockResolvedValue(mockCalcResponse);
  mockFetchMETRCurve.mockResolvedValue(mockCurveWithDeadZones);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('METRCalculator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders controls: income slider, province selector, family type selector, children stepper', async () => {
    setupDefaultMocks();
    render(<METRCalculator />);

    await waitFor(() => {
      expect(screen.queryByTestId('skeleton-loader')).not.toBeInTheDocument();
    });

    expect(screen.getByLabelText('Income slider')).toBeInTheDocument();
    expect(screen.getByLabelText('Province selector')).toBeInTheDocument();
    expect(screen.getByLabelText('Family type selector')).toBeInTheDocument();
    expect(screen.getByLabelText('Increase children')).toBeInTheDocument();
    expect(screen.getByLabelText('Decrease children')).toBeInTheDocument();
  });

  it('updates displayed income when slider changes to $50k', async () => {
    setupDefaultMocks();
    render(<METRCalculator />);

    const slider = screen.getByLabelText('Income slider');
    // fireEvent is more reliable for range inputs than userEvent
    const { fireEvent } = await import('@testing-library/react');
    fireEvent.change(slider, { target: { value: '50000' } });

    expect(screen.getByTestId('income-display')).toHaveTextContent('$50,000');
  });

  it('triggers API fetch with province=BC when province changes', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();
    render(<METRCalculator />);

    await waitFor(() => {
      expect(mockFetchMETRCurve).toHaveBeenCalled();
    });

    mockFetchMETRCurve.mockClear();
    mockFetchMETRCalculation.mockClear();

    const provinceSelect = screen.getByLabelText('Province selector');
    await user.selectOptions(provinceSelect, 'BC');

    await waitFor(() => {
      expect(mockFetchMETRCurve).toHaveBeenCalledWith(
        expect.objectContaining({ province: 'BC' }),
      );
    });
  });

  it('renders SVG chart with correct path element for curve data', async () => {
    setupDefaultMocks();
    render(<METRCalculator />);

    await waitFor(() => {
      expect(screen.queryByTestId('skeleton-loader')).not.toBeInTheDocument();
    });

    const svg = screen.getByTestId('metr-chart-svg');
    expect(svg).toBeInTheDocument();
    expect(svg.tagName.toLowerCase()).toBe('svg');

    // One path element for the curve
    const paths = svg.querySelectorAll('[data-testid="metr-curve-path"]');
    expect(paths).toHaveLength(1);
  });

  it('shows METR value and net income in KPI cards', async () => {
    setupDefaultMocks();
    render(<METRCalculator />);

    await waitFor(() => {
      expect(screen.queryByTestId('skeleton-loader')).not.toBeInTheDocument();
    });

    expect(screen.getByTestId('kpi-metr')).toHaveTextContent('42.5%');
    expect(screen.getByTestId('kpi-net-income')).toHaveTextContent('$39,200');
  });

  it('highlights dead zones with red shading rects', async () => {
    setupDeadZoneMocks();
    render(<METRCalculator />);

    await waitFor(() => {
      expect(screen.queryByTestId('skeleton-loader')).not.toBeInTheDocument();
    });

    const deadZoneRects = screen.getAllByTestId('dead-zone-rect');
    expect(deadZoneRects.length).toBeGreaterThanOrEqual(1);
  });

  it('stacks controls vertically on mobile (375px)', async () => {
    setupDefaultMocks();
    render(<METRCalculator />);

    await waitFor(() => {
      expect(screen.queryByTestId('skeleton-loader')).not.toBeInTheDocument();
    });

    const controls = screen.getByTestId('calculator-controls');
    // The flex-col class ensures vertical stacking on mobile
    expect(controls.className).toContain('flex-col');
  });

  it('shows skeleton loader (not spinner) during data fetch', () => {
    // Mock API calls that never resolve to keep loading state
    mockFetchMETRCalculation.mockReturnValue(new Promise(() => {}));
    mockFetchMETRCurve.mockReturnValue(new Promise(() => {}));

    render(<METRCalculator />);

    expect(screen.getByTestId('skeleton-loader')).toBeInTheDocument();
    // No spinner should be present
    expect(screen.queryByTestId('spinner')).not.toBeInTheDocument();
    expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
  });

  it('toggles methodology drawer when clicking "How is METR calculated?"', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();
    render(<METRCalculator />);

    // Drawer content should not be visible initially
    expect(screen.queryByTestId('methodology-content')).not.toBeInTheDocument();

    // Click toggle
    await user.click(screen.getByText('How is METR calculated?'));

    expect(screen.getByTestId('methodology-content')).toBeInTheDocument();
    expect(screen.getByText('Methodology')).toBeInTheDocument();

    // Click again to close
    await user.click(screen.getByText('How is METR calculated?'));

    expect(screen.queryByTestId('methodology-content')).not.toBeInTheDocument();
  });
});

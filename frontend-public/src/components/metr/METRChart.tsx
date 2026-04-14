'use client';

import { useEffect, useRef } from 'react';
import type { CurvePoint, DeadZone } from '@/lib/types/metr';

interface METRChartProps {
  curve: CurvePoint[];
  deadZones: DeadZone[];
}

export default function METRChart({ curve, deadZones }: METRChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || curve.length === 0) return;

    const svg = svgRef.current;
    // Clear previous render
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    const width = 800;
    const height = 400;
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

    const maxGross = Math.max(...curve.map((p) => p.gross));
    const maxMetr = Math.max(...curve.map((p) => p.metr), 100);

    const xScale = (v: number) => (v / maxGross) * width;
    const yScale = (v: number) => height - (v / maxMetr) * height;

    // Draw dead zone shading
    for (const dz of deadZones) {
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', String(xScale(dz.start)));
      rect.setAttribute('y', '0');
      rect.setAttribute('width', String(xScale(dz.end) - xScale(dz.start)));
      rect.setAttribute('height', String(height));
      rect.setAttribute('class', 'dead-zone-shading');
      rect.setAttribute('fill', 'var(--data-warning, #F97316)');
      rect.setAttribute('opacity', '0.15');
      rect.setAttribute('data-testid', 'dead-zone-rect');
      svg.appendChild(rect);
    }

    // Build path data
    const pathD = curve
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.gross)} ${yScale(p.metr)}`)
      .join(' ');

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', pathD);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', 'var(--accent, #FBBF24)');
    path.setAttribute('stroke-width', '2');
    path.setAttribute('data-testid', 'metr-curve-path');
    svg.appendChild(path);
  }, [curve, deadZones]);

  return (
    <div data-testid="metr-chart">
      <svg
        ref={svgRef}
        role="img"
        aria-label="METR curve chart"
        className="w-full h-auto"
        data-testid="metr-chart-svg"
      />
      <p className="text-xs text-text-secondary mt-2 font-body">
        Source: Summa Vision METR Calculator, 2025 tax year
      </p>
    </div>
  );
}

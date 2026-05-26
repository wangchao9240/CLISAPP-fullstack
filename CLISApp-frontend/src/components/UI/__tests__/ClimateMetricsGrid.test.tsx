import React from 'react';
import { create } from 'react-test-renderer';
import type { RegionClimateOverview } from '../../../types/region.types';
import { ClimateMetricsGrid } from '../ClimateMetricsGrid';

const climate: RegionClimateOverview = {
  primary: { layer: 'pm25', name: 'PM2.5', value: 35, unit: 'µg/m³', riskLevel: 'Moderate' },
  secondary: [
    { layer: 'temperature', name: 'Temperature', value: 25.3, unit: '°C', riskLevel: 'Good' },
    { layer: 'uv', name: 'UV', value: 6, unit: 'UVI', riskLevel: 'Unhealthy' },
    { layer: 'humidity', name: 'Humidity', value: 62, unit: '%', riskLevel: 'Good' },
    { layer: 'precipitation', name: 'Precip', value: 0, unit: 'mm/day', riskLevel: 'Good' },
  ],
};

const findText = (renderer: ReturnType<typeof create>, text: string) =>
  renderer.root.findAllByType('Text' as any).filter((node) => node.props.children === text);

describe('ClimateMetricsGrid', () => {
  it('renders exactly five metric tiles with Stitch-order labels', () => {
    const renderer = create(<ClimateMetricsGrid climate={climate} />);
    // Labels must match spec ordering PM2.5, TEMP, UV INDEX, HUMIDITY, PRECIP
    expect(findText(renderer, 'PM2.5').length).toBe(1);
    expect(findText(renderer, 'TEMP').length).toBe(1);
    expect(findText(renderer, 'UV INDEX').length).toBe(1);
    expect(findText(renderer, 'HUMIDITY').length).toBe(1);
    expect(findText(renderer, 'PRECIP').length).toBe(1);
    renderer.unmount();
  });

  it('displays the precipitation unit as mm/day', () => {
    const renderer = create(<ClimateMetricsGrid climate={climate} />);
    expect(findText(renderer, 'mm/day').length).toBe(1);
    renderer.unmount();
  });

  it('formats temperature and precipitation values with one decimal', () => {
    const renderer = create(<ClimateMetricsGrid climate={climate} />);
    expect(findText(renderer, '25.3').length).toBe(1);
    expect(findText(renderer, '0.0').length).toBe(1);
    renderer.unmount();
  });

  it('renders em-dash for layers missing from the climate overview', () => {
    const partial: RegionClimateOverview = {
      primary: climate.primary,
      secondary: [], // temp, uv, humidity, precip all missing
    };
    const renderer = create(<ClimateMetricsGrid climate={partial} />);
    // 4 missing → at least 4 em-dash value nodes
    expect(findText(renderer, '—').length).toBeGreaterThanOrEqual(4);
    renderer.unmount();
  });
});

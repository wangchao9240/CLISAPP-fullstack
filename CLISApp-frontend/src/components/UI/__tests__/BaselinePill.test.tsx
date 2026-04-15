// CLISApp-frontend/src/components/UI/__tests__/BaselinePill.test.tsx
import React from 'react';
import { create } from 'react-test-renderer';
import type { RegionClimateOverview } from '../../../types/region.types';
import { BaselinePill } from '../BaselinePill';

jest.mock('../../../../assets/data/climate_baseline.json', () => ({
  baselines: { ssc_A: { bmT: 22 } },
}));

const findText = (renderer: ReturnType<typeof create>, text: string) =>
  renderer.root
    .findAllByType('Text' as any)
    .filter((node) => node.props.children === text);

const climate = (tempValue?: number): RegionClimateOverview => ({
  primary: tempValue === undefined
    ? null
    : { layer: 'temperature', name: 'Temperature', value: tempValue, unit: '°C' },
  secondary: [],
});

describe('BaselinePill', () => {
  it('renders warm delta label and above subtitle', () => {
    const renderer = create(<BaselinePill regionSscId="ssc_A" climate={climate(26)} />);
    expect(findText(renderer, '+4.0°C').length).toBe(1);
    expect(findText(renderer, 'ABOVE 1890-1960 BASELINE').length).toBe(1);
    renderer.unmount();
  });

  it('renders cool delta label and below subtitle', () => {
    const renderer = create(<BaselinePill regionSscId="ssc_A" climate={climate(16)} />);
    expect(findText(renderer, '-6.0°C').length).toBe(1);
    expect(findText(renderer, 'BELOW 1890-1960 BASELINE').length).toBe(1);
    renderer.unmount();
  });

  it('hides the delta label for the neutral variant', () => {
    const renderer = create(<BaselinePill regionSscId="ssc_A" climate={climate(22)} />);
    expect(findText(renderer, 'NEAR 1890-1960 BASELINE').length).toBe(1);
    // No ±X.X°C label is rendered
    expect(renderer.root.findAll((n) => typeof n.props?.children === 'string' && /°C$/.test(n.props.children)).length).toBe(0);
    renderer.unmount();
  });

  it('renders baseline-unavailable subtitle when region has no baseline', () => {
    const renderer = create(<BaselinePill regionSscId="ssc_missing" climate={climate(20)} />);
    expect(findText(renderer, 'BASELINE UNAVAILABLE').length).toBe(1);
    renderer.unmount();
  });
});

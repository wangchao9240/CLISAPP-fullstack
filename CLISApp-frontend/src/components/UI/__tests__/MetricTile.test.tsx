import React from 'react';
import { create } from 'react-test-renderer';
import { MetricTile } from '../MetricTile';

const findText = (renderer: ReturnType<typeof create>, text: string) =>
  renderer.root.findAllByType('Text' as any).filter((node) => node.props.children === text);

describe('MetricTile', () => {
  it('renders label, value, unit and risk text', () => {
    const renderer = create(
      <MetricTile label="PM2.5" value="35" unit="µg/m³" riskLevel="Moderate" />,
    );
    expect(findText(renderer, 'PM2.5').length).toBe(1);
    expect(findText(renderer, '35').length).toBe(1);
    expect(findText(renderer, 'µg/m³').length).toBe(1);
    expect(findText(renderer, 'MODERATE').length).toBe(1);
    renderer.unmount();
  });

  it('renders em-dash for missing value and unknown risk', () => {
    const renderer = create(
      <MetricTile label="UV INDEX" value="—" unit={null} riskLevel={undefined} />,
    );
    expect(findText(renderer, 'UV INDEX').length).toBe(1);
    expect(findText(renderer, '—').length).toBeGreaterThanOrEqual(1);
    renderer.unmount();
  });

  it('has accessible label describing the metric', () => {
    const renderer = create(
      <MetricTile label="TEMP" value="25.3" unit="°C" riskLevel="Good" />,
    );
    const tile = renderer.root.findByProps({ accessibilityRole: 'text' });
    expect(tile.props.accessibilityLabel).toBe('TEMP: 25.3 °C, Good');
    renderer.unmount();
  });
});

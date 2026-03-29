import React from 'react';
import { create } from 'react-test-renderer';
import { RegionClimateOverview } from '../../../types/region.types';

jest.mock('react-native-vector-icons/MaterialCommunityIcons', () => {
  const { Text } = require('react-native');
  return ({ name, ...props }: any) => <Text {...props}>{name}</Text>;
});

jest.mock('../../../../assets/data/climate_baseline.json', () => ({
  baselines: {
    ssc_30002: { bmT: 27.0 },
    ssc_30003: { bmT: 27.0 },
    ssc_30004: { bmT: 27.0 },
  },
}));

const { ClimateChangeIndicator } =
  require('../ClimateChangeIndicator') as typeof import('../ClimateChangeIndicator');

const makeClimateOverview = (temperatureValue?: number): RegionClimateOverview => ({
  primary: {
    layer: 'pm25',
    name: 'PM2.5 Concentration',
    value: 35,
    unit: 'ug/m3',
  },
  secondary:
    temperatureValue === undefined
      ? []
      : [
          {
            layer: 'temperature',
            name: '2m Temperature',
            value: temperatureValue,
            unit: '°C',
          },
        ],
});

const findTextNode = (renderer: ReturnType<typeof create>, expectedText: string) =>
  renderer.root
    .findAllByType('Text' as any)
    .find((node) => node.props.children === expectedText);

describe('ClimateChangeIndicator', () => {
  it('renders a warm indicator with a positive diff rounded to one decimal place', () => {
    const renderer = create(
      <ClimateChangeIndicator
        regionSscId="ssc_30002"
        climate={makeClimateOverview(27.64)}
      />,
    );

    expect(findTextNode(renderer, 'arrow-top-right')?.props.color).toBe('#FF7043');
    expect(findTextNode(renderer, '+0.6°C')).toBeDefined();
    expect(findTextNode(renderer, 'above 1890-1960 baseline')).toBeDefined();
  });

  it('renders a cool indicator with a negative diff rounded to one decimal place', () => {
    const renderer = create(
      <ClimateChangeIndicator
        regionSscId="ssc_30003"
        climate={makeClimateOverview(26.24)}
      />,
    );

    expect(findTextNode(renderer, 'arrow-bottom-right')?.props.color).toBe('#81D4FA');
    expect(findTextNode(renderer, '-0.8°C')).toBeDefined();
    expect(findTextNode(renderer, 'below 1890-1960 baseline')).toBeDefined();
  });

  it('renders a neutral indicator when the temperature is near baseline', () => {
    const renderer = create(
      <ClimateChangeIndicator
        regionSscId="ssc_30004"
        climate={makeClimateOverview(27.05)}
      />,
    );

    expect(findTextNode(renderer, 'approximately-equal')?.props.color).toBe('#78909C');
    expect(findTextNode(renderer, 'Near 1890-1960 baseline')).toBeDefined();
    expect(
      renderer.root
        .findAllByType('Text' as any)
        .filter((node) => node.props.children === '+0.1°C'),
    ).toHaveLength(0);
  });

  it('renders the fallback message when the region baseline is missing', () => {
    const renderer = create(
      <ClimateChangeIndicator
        regionSscId="ssc_99999"
        climate={makeClimateOverview(28)}
      />,
    );

    expect(findTextNode(renderer, 'Baseline data not available for this region')).toBeDefined();
  });

  it('renders the fallback message when the region id is null', () => {
    const renderer = create(
      <ClimateChangeIndicator
        regionSscId={null}
        climate={makeClimateOverview(28)}
      />,
    );

    expect(findTextNode(renderer, 'Baseline data not available for this region')).toBeDefined();
  });

  it('renders the fallback message when temperature data is unavailable', () => {
    const renderer = create(
      <ClimateChangeIndicator
        regionSscId="ssc_30002"
        climate={makeClimateOverview(undefined)}
      />,
    );

    expect(findTextNode(renderer, 'Baseline data not available for this region')).toBeDefined();
  });
});

import type { RegionClimateOverview } from '../../types/region.types';
import { getClimateDeltaState } from '../climateDelta';

jest.mock('../../../assets/data/climate_baseline.json', () => ({
  baselines: {
    ssc_10001: { bmT: 22 },
    ssc_no_baseline: {},
  },
}));

const makeClimate = (temperatureValue?: number): RegionClimateOverview => ({
  primary: temperatureValue === undefined
    ? null
    : { layer: 'temperature', name: 'Temperature', value: temperatureValue, unit: '°C' },
  secondary: [],
});

describe('getClimateDeltaState', () => {
  it('returns unavailable when regionId is null', () => {
    const state = getClimateDeltaState(null, makeClimate(25));
    expect(state.variant).toBe('unavailable');
    expect(state.deltaLabel).toBeNull();
  });

  it('returns unavailable when no baseline exists for region', () => {
    const state = getClimateDeltaState('ssc_unknown', makeClimate(25));
    expect(state.variant).toBe('unavailable');
  });

  it('returns unavailable when temperature stat is missing', () => {
    const state = getClimateDeltaState('ssc_10001', makeClimate(undefined));
    expect(state.variant).toBe('unavailable');
  });

  it('returns warm variant when current > baseline + threshold', () => {
    const state = getClimateDeltaState('ssc_10001', makeClimate(24));
    expect(state.variant).toBe('warm');
    expect(state.deltaLabel).toBe('+2.0°C');
    expect(state.subtitleText).toBe('ABOVE 1890-1960 BASELINE');
  });

  it('returns cool variant when current < baseline - threshold', () => {
    const state = getClimateDeltaState('ssc_10001', makeClimate(16));
    expect(state.variant).toBe('cool');
    expect(state.deltaLabel).toBe('-6.0°C');
    expect(state.subtitleText).toBe('BELOW 1890-1960 BASELINE');
  });

  it('returns neutral within ±0.1°C', () => {
    const state = getClimateDeltaState('ssc_10001', makeClimate(22.05));
    expect(state.variant).toBe('neutral');
    expect(state.deltaLabel).toBeNull();
    expect(state.subtitleText).toBe('NEAR 1890-1960 BASELINE');
  });
});

import type { RegionClimateOverview, RegionClimateStat } from '../../types/region.types';
import { getWorstRiskStat } from '../riskPriority';

const stat = (layer: RegionClimateStat['layer'], risk: string | undefined, value = 0): RegionClimateStat => ({
  layer,
  name: layer,
  value,
  unit: '',
  riskLevel: risk,
});

describe('getWorstRiskStat', () => {
  it('returns null when climate is null', () => {
    expect(getWorstRiskStat(null)).toBeNull();
  });

  it('returns null when every stat has Unknown or missing risk', () => {
    const climate: RegionClimateOverview = {
      primary: stat('pm25', undefined),
      secondary: [stat('temperature', 'Unknown')],
    };
    expect(getWorstRiskStat(climate)).toBeNull();
  });

  it('picks Hazardous over Unhealthy and Moderate', () => {
    const climate: RegionClimateOverview = {
      primary: stat('pm25', 'Unhealthy'),
      secondary: [stat('uv', 'Hazardous'), stat('temperature', 'Moderate')],
    };
    expect(getWorstRiskStat(climate)?.layer).toBe('uv');
  });

  it('picks Moderate when only Good/Moderate are present', () => {
    const climate: RegionClimateOverview = {
      primary: stat('pm25', 'Good'),
      secondary: [stat('humidity', 'Moderate')],
    };
    expect(getWorstRiskStat(climate)?.layer).toBe('humidity');
  });

  it('returns null when every layer is Good', () => {
    const climate: RegionClimateOverview = {
      primary: stat('pm25', 'Good'),
      secondary: [stat('uv', 'Good'), stat('temperature', 'Good')],
    };
    expect(getWorstRiskStat(climate)).toBeNull();
  });

  it('breaks ties by CLIMATE_LAYER_ORDER (pm25 → precipitation → uv → humidity → temperature)', () => {
    const climate: RegionClimateOverview = {
      primary: stat('temperature', 'Unhealthy'),
      secondary: [stat('pm25', 'Unhealthy'), stat('uv', 'Unhealthy')],
    };
    expect(getWorstRiskStat(climate)?.layer).toBe('pm25');
  });
});

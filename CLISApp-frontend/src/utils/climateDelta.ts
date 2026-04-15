import climateBaseline from '../../assets/data/climate_baseline.json';
import { getActiveClimateStat } from '../constants/climateData';
import type { RegionClimateOverview } from '../types/region.types';

const THRESHOLD = 0.1;
const baselineData = climateBaseline as {
  baselines: Record<string, { bmT?: number }>;
};

export type ClimateDeltaVariant = 'warm' | 'cool' | 'neutral' | 'unavailable';

export interface ClimateDeltaState {
  variant: ClimateDeltaVariant;
  deltaLabel: string | null;
  subtitleText: string;
}

const formatDiff = (diff: number): string =>
  `${diff > 0 ? '+' : ''}${diff.toFixed(1)}°C`;

export const getClimateDeltaState = (
  regionSscId: string | null,
  climate: RegionClimateOverview | null,
): ClimateDeltaState => {
  if (!regionSscId) {
    return { variant: 'unavailable', deltaLabel: null, subtitleText: 'BASELINE UNAVAILABLE' };
  }

  const baselineTemperature = baselineData.baselines[regionSscId]?.bmT;
  const currentTemperature = getActiveClimateStat(climate, 'temperature')?.value;

  if (baselineTemperature === undefined || currentTemperature === undefined) {
    return { variant: 'unavailable', deltaLabel: null, subtitleText: 'BASELINE UNAVAILABLE' };
  }

  const diff = currentTemperature - baselineTemperature;

  if (diff > THRESHOLD) {
    return { variant: 'warm', deltaLabel: formatDiff(diff), subtitleText: 'ABOVE 1890-1960 BASELINE' };
  }
  if (diff < -THRESHOLD) {
    return { variant: 'cool', deltaLabel: formatDiff(diff), subtitleText: 'BELOW 1890-1960 BASELINE' };
  }
  return { variant: 'neutral', deltaLabel: null, subtitleText: 'NEAR 1890-1960 BASELINE' };
};

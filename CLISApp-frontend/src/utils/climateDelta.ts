import climateBaseline from '../../assets/data/climate_baseline.json';
import climateBaselineDaily from '../../assets/data/climate_baseline_daily.json';
import { getActiveClimateStat } from '../constants/climateData';
import type { RegionClimateOverview } from '../types/region.types';

const THRESHOLD = 0.1;
const baselineData = climateBaseline as {
  baselines: Record<string, { bmT?: number }>;
};
const dailyBaselineData = climateBaselineDaily as {
  baselines: Record<
    string,
    {
      tmean?: Array<number | null>;
      MT?: Array<number | null>;
      mT?: Array<number | null>;
      rf?: Array<number | null>;
    }
  >;
};

export type ClimateDeltaVariant = 'warm' | 'cool' | 'neutral' | 'unavailable';
export type ClimateBaselineSource = 'daily' | 'yearly' | 'unavailable';

export interface ClimateDeltaState {
  variant: ClimateDeltaVariant;
  deltaLabel: string | null;
  subtitleText: string;
  source: ClimateBaselineSource;
}

const formatDiff = (diff: number): string =>
  `${diff > 0 ? '+' : ''}${diff.toFixed(1)}°C`;

export const doyFromDate = (d: Date): number => {
  // Use local-date components — Queensland is UTC+10; UTC-based math
  // would flip the day for ~10 hours either side of local midnight.
  const start = new Date(d.getFullYear(), 0, 0);
  return Math.floor((d.getTime() - start.getTime()) / 86_400_000);
};

export const formatDailyBaselineDateLabel = (date: Date): string =>
  new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(
    date,
  );

export const getDailyBaseline = (
  regionSscId: string | null,
  doy: number,
): { tmean?: number; MT?: number; mT?: number; rf?: number } | null => {
  if (!regionSscId || doy < 1 || doy > 366) {
    return null;
  }

  const baseline = dailyBaselineData.baselines[regionSscId];
  if (!baseline) {
    return null;
  }

  const dayIndex = doy - 1;
  const dailyValues = {
    tmean: baseline.tmean?.[dayIndex] ?? undefined,
    MT: baseline.MT?.[dayIndex] ?? undefined,
    mT: baseline.mT?.[dayIndex] ?? undefined,
    rf: baseline.rf?.[dayIndex] ?? undefined,
  };

  return Object.values(dailyValues).some(value => value !== undefined)
    ? dailyValues
    : null;
};

const buildSubtitle = (
  variant: Exclude<ClimateDeltaVariant, 'unavailable'>,
  source: Extract<ClimateBaselineSource, 'daily' | 'yearly'>,
  date: Date,
): string => {
  const direction =
    variant === 'warm' ? 'ABOVE' : variant === 'cool' ? 'BELOW' : 'NEAR';

  if (source === 'daily') {
    return `${direction} TYPICAL ${formatDailyBaselineDateLabel(
      date,
    ).toUpperCase()} (1890-1960)`;
  }

  return variant === 'neutral'
    ? 'NEAR 1890-1960 BASELINE'
    : `${direction} 1890-1960 BASELINE`;
};

export const getClimateDeltaState = (
  regionSscId: string | null,
  climate: RegionClimateOverview | null,
  date: Date = new Date(),
): ClimateDeltaState => {
  if (!regionSscId) {
    return {
      variant: 'unavailable',
      deltaLabel: null,
      subtitleText: 'BASELINE UNAVAILABLE',
      source: 'unavailable',
    };
  }

  const dailyBaseline = getDailyBaseline(regionSscId, doyFromDate(date));
  const dailyTemperature = dailyBaseline?.tmean;
  const yearlyTemperature = baselineData.baselines[regionSscId]?.bmT;
  const baselineTemperature = dailyTemperature ?? yearlyTemperature;
  const source: Extract<ClimateBaselineSource, 'daily' | 'yearly'> | null =
    dailyTemperature !== undefined
      ? 'daily'
      : yearlyTemperature !== undefined
      ? 'yearly'
      : null;
  const currentTemperature = getActiveClimateStat(
    climate,
    'temperature',
  )?.value;

  if (
    baselineTemperature === undefined ||
    currentTemperature === undefined ||
    source === null
  ) {
    return {
      variant: 'unavailable',
      deltaLabel: null,
      subtitleText: 'BASELINE UNAVAILABLE',
      source: 'unavailable',
    };
  }

  const diff = currentTemperature - baselineTemperature;

  if (diff > THRESHOLD) {
    return {
      variant: 'warm',
      deltaLabel: formatDiff(diff),
      subtitleText: buildSubtitle('warm', source, date),
      source,
    };
  }
  if (diff < -THRESHOLD) {
    return {
      variant: 'cool',
      deltaLabel: formatDiff(diff),
      subtitleText: buildSubtitle('cool', source, date),
      source,
    };
  }
  return {
    variant: 'neutral',
    deltaLabel: null,
    subtitleText: buildSubtitle('neutral', source, date),
    source,
  };
};

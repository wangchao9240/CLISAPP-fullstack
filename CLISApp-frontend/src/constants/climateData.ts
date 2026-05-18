// Climate data layer configurations
import { ClimateDataConfig, ClimateLayer } from '../types/climate.types';
import { RegionClimateOverview, RegionClimateStat } from '../types/region.types';

const PM25_COLOR_SCALE = ['#00ff00', '#ffff00', '#ff6600', '#ff0000', '#800080'];
const PM25_DEFAULT_THRESHOLDS = [0, 12, 35, 55, 150];
let pm25Thresholds = [...PM25_DEFAULT_THRESHOLDS];

const PRECIP_COLOR_SCALE = ['#ffffff', '#87ceeb', '#4169e1', '#0000ff', '#00008b'];
const PRECIP_DEFAULT_THRESHOLDS = [0, 2, 10, 50, 100];
let precipitationThresholds = [...PRECIP_DEFAULT_THRESHOLDS];

export const CLIMATE_LAYER_ORDER: ClimateLayer[] = ['pm25', 'precipitation', 'uv', 'humidity', 'temperature'];

export const CLIMATE_LAYERS: Record<ClimateLayer, ClimateDataConfig> = {
  pm25: {
    name: 'PM2.5 Concentration',
    colorScale: PM25_COLOR_SCALE,
    unit: 'µg/m³',
    thresholds: pm25Thresholds,
    description: 'Particulate matter smaller than 2.5 micrometers',
  },
  precipitation: {
    name: 'Precipitation',
    colorScale: PRECIP_COLOR_SCALE,
    unit: 'mm/day',
    thresholds: precipitationThresholds,
    description: 'Daily precipitation total',
  },
  uv: {
    name: 'UV Index',
    colorScale: ['#289500', '#f7e400', '#f85900', '#d8001d', '#6b49c8'],
    unit: 'UVI',
    thresholds: [0, 3, 6, 8, 11],
    description: 'Ultraviolet radiation index',
  },
  humidity: {
    name: 'Relative Humidity',
    colorScale: ['#8B4513', '#DAA520', '#FFD700', '#87CEEB', '#4169E1'],
    unit: '%',
    thresholds: [0, 30, 50, 70, 90],
    description: 'Relative humidity percentage',
  },
  temperature: {
    name: '2m Temperature',
    colorScale: ['#0000ff', '#87ceeb', '#ffff00', '#ff6600', '#ff0000'],
    unit: '°C',
    thresholds: [0, 10, 20, 30, 40],
    description: 'Air temperature at 2 meters above ground',
  },
};

export const DEFAULT_LAYER: ClimateLayer = 'pm25';

export const setPm25Thresholds = (thresholds: number[]) => {
  if (!Array.isArray(thresholds) || thresholds.length !== PM25_COLOR_SCALE.length) {
    return;
  }
  pm25Thresholds = thresholds.map((value) => Number(value));
  CLIMATE_LAYERS.pm25 = {
    ...CLIMATE_LAYERS.pm25,
    thresholds: pm25Thresholds,
  };
};

export const getPm25Thresholds = () => pm25Thresholds;

export const resetPm25ThresholdsToDefault = () => {
  setPm25Thresholds([...PM25_DEFAULT_THRESHOLDS]);
};

export const setPrecipitationThresholds = (thresholds: number[]) => {
  if (!Array.isArray(thresholds) || thresholds.length !== PRECIP_COLOR_SCALE.length) {
    return;
  }
  precipitationThresholds = thresholds.map((value) => Number(value));
  CLIMATE_LAYERS.precipitation = {
    ...CLIMATE_LAYERS.precipitation,
    thresholds: precipitationThresholds,
  };
};

export const getPrecipitationThresholds = () => precipitationThresholds;

export const resetPrecipitationThresholdsToDefault = () => {
  setPrecipitationThresholds([...PRECIP_DEFAULT_THRESHOLDS]);
};

export const LAYER_CATEGORY_SUFFIX: Record<ClimateLayer, string> = {
  pm25: 'Air Quality',
  uv: 'UV Exposure',
  temperature: 'Temperature',
  humidity: 'Humidity',
  precipitation: 'Rainfall',
};

export const getActiveClimateStat = (
  climate: RegionClimateOverview | null,
  activeLayer: ClimateLayer,
): RegionClimateStat | null => {
  if (!climate) return null;
  if (climate.primary?.layer === activeLayer) return climate.primary;
  return climate.secondary.find((stat) => stat.layer === activeLayer) ?? null;
};

export const formatBadgeText = (
  value: number | undefined,
  unit: string | undefined,
  category: string | undefined,
  layer: ClimateLayer,
): string => {
  const suffix = LAYER_CATEGORY_SUFFIX[layer];
  const categoryLabel = category ? `${category} ${suffix}` : suffix;
  if (value === undefined || unit === undefined) return categoryLabel;
  return `${value} ${unit} / ${categoryLabel}`;
};

import { useEffect } from 'react';
import { useSettingsStore } from '../store/settingsStore';
import {
  setPm25Thresholds,
  resetPm25ThresholdsToDefault,
  getPm25Thresholds,
  setPrecipitationThresholds,
  resetPrecipitationThresholdsToDefault,
  getPrecipitationThresholds,
} from '../constants/climateData';

type ClimateLayerId = 'pm25' | 'precipitation';

const THRESHOLD_HANDLERS: Record<ClimateLayerId, {
  set: (values: number[]) => void;
  get: () => number[];
  reset: () => void;
  colorScaleLength: number;
}> = {
  pm25: {
    set: setPm25Thresholds,
    get: getPm25Thresholds,
    reset: resetPm25ThresholdsToDefault,
    colorScaleLength: 5,
  },
  precipitation: {
    set: setPrecipitationThresholds,
    get: getPrecipitationThresholds,
    reset: resetPrecipitationThresholdsToDefault,
    colorScaleLength: 5,
  },
};

const endpointMap: Record<ClimateLayerId, string> = {
  pm25: 'pm25',
  precipitation: 'precipitation',
};

export const useDynamicThreshold = (layer: ClimateLayerId) => {
  const { tileServerUrl } = useSettingsStore();
  const handlers = THRESHOLD_HANDLERS[layer];

  useEffect(() => {
    if (!tileServerUrl) {
      return;
    }

    let cancelled = false;

    const fetchThresholds = async () => {
      try {
        const baseUrl = tileServerUrl.endsWith('/') ? tileServerUrl.slice(0, -1) : tileServerUrl;
        const response = await fetch(`${baseUrl}/${endpointMap[layer]}/info`);
        if (!response.ok) {
          return;
        }
        const json = await response.json();
        const dynamic = json?.dynamic_thresholds || json?.tile_format?.color_scheme?.thresholds;
        if (
          !cancelled &&
          Array.isArray(dynamic) &&
          dynamic.length === handlers.colorScaleLength
        ) {
          handlers.set(dynamic.map((value: number) => Number(value)));
        }
      } catch (error) {
        console.warn(`Failed to fetch ${layer} thresholds`, error);
      }
    };

    fetchThresholds();
    return () => {
      cancelled = true;
      handlers.reset();
    };
  }, [tileServerUrl, layer, handlers]);

  return handlers.get();
};


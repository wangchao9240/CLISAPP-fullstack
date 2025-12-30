import { ClimateLayer } from './climate.types';

export interface RegionClimateStat {
  layer: ClimateLayer;
  name: string;
  value: number;
  unit: string;
  category?: string;
  description?: string;
  lastUpdated?: string;
}

export interface RegionClimateOverview {
  primary: RegionClimateStat | null;
  secondary: RegionClimateStat[];
}

export interface RegionInfoPanelState {
  visible: boolean;
  regionId: string | null;
  regionName: string | null;
  regionType: 'lga' | 'suburb' | null;
  climate: RegionClimateOverview | null;
  loading: boolean;
  error?: string | null;
}

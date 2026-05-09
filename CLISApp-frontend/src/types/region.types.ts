import { ClimateLayer } from './climate.types';

export interface RegionClimateStat {
  layer: ClimateLayer;
  name: string;
  value: number;
  unit: string;
  category?: string;
  riskLevel?: string;
  advice?: string;
  description?: string;
  lastUpdated?: string;
}

export interface RegionClimateOverview {
  primary: RegionClimateStat | null;
  secondary: RegionClimateStat[];
  /** Wind speed in km/h — optional, only present when the API includes it. */
  wind_speed?: number | null;
}

export interface RegionInfoPanelState {
  visible: boolean;
  regionId: string | null;
  regionName: string | null;
  regionType: string | null;
  latitude: number | null;
  longitude: number | null;
  climate: RegionClimateOverview | null;
  loading: boolean;
  error?: string | null;
}

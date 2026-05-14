import { useMapStore } from '../../store/mapStore';
import type { RegionClimateOverview } from '../../types/region.types';
import { useDebugStore, type RiskKey } from '../debugStore';
import riskExtreme from '../fixtures/risk-extreme.json';
import riskHigh from '../fixtures/risk-high.json';
import riskLow from '../fixtures/risk-low.json';
import riskModerate from '../fixtures/risk-moderate.json';

const FIXTURES: Record<RiskKey, RegionClimateOverview> = {
  low: riskLow as RegionClimateOverview,
  moderate: riskModerate as RegionClimateOverview,
  high: riskHigh as RegionClimateOverview,
  extreme: riskExtreme as RegionClimateOverview,
};

const DEBUG_REGION = {
  regionId: 'DEBUG-3110',
  regionName: 'Demo Suburb (Debug)',
  regionType: 'ssc',
  latitude: -27.47,
  longitude: 153.03,
};

export const applyRiskCycle = (level: RiskKey): void => {
  const debugStore = useDebugStore.getState();
  if (debugStore.overrides.risk === level) return;

  const mapStore = useMapStore.getState();
  debugStore.captureSnapshotIfNone(mapStore.regionInfo);
  mapStore.openRegionInfo({
    ...DEBUG_REGION,
    climate: FIXTURES[level],
  });
  debugStore.setRiskOverride(level);
};

import { CLIMATE_LAYER_ORDER } from '../constants/climateData';
import type { RegionClimateOverview, RegionClimateStat } from '../types/region.types';

// Higher wins. Unknown/missing never win against anything meaningful.
const PRIORITY: Record<string, number> = {
  Hazardous: 4,
  Unhealthy: 3,
  Moderate: 2,
  Good: 0,
  Unknown: 0,
};

const priorityOf = (risk: string | undefined): number =>
  risk && PRIORITY[risk] !== undefined ? PRIORITY[risk] : 0;

const layerRank = (layer: RegionClimateStat['layer']): number => {
  const idx = CLIMATE_LAYER_ORDER.indexOf(layer);
  return idx === -1 ? Number.MAX_SAFE_INTEGER : idx;
};

const collectStats = (climate: RegionClimateOverview | null): RegionClimateStat[] => {
  if (!climate) return [];
  return [climate.primary, ...climate.secondary].filter(
    (s): s is RegionClimateStat => s !== null && s !== undefined,
  );
};

export const getWorstRiskStat = (
  climate: RegionClimateOverview | null,
): RegionClimateStat | null => {
  const stats = collectStats(climate);
  let winner: RegionClimateStat | null = null;
  let winnerPriority = 1; // must beat Good (0) to be considered "worst"

  for (const s of stats) {
    const p = priorityOf(s.riskLevel);
    if (p < winnerPriority) continue;
    if (p > winnerPriority) {
      winner = s;
      winnerPriority = p;
      continue;
    }
    if (winner && layerRank(s.layer) < layerRank(winner.layer)) {
      winner = s;
    }
  }

  return winner;
};

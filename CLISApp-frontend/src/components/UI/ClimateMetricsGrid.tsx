import React from 'react';
import { StyleSheet, View } from 'react-native';
import { MetricTile } from './MetricTile';
import type { ClimateLayer } from '../../types/climate.types';
import type { RegionClimateOverview, RegionClimateStat } from '../../types/region.types';

interface ClimateMetricsGridProps {
  climate: RegionClimateOverview | null;
}

interface TileSpec {
  layer: ClimateLayer;
  label: string;
  unitOverride?: string;
  decimals: 0 | 1;
}

// Stitch reading order — row 1: pm25, temp, uv | row 2: humidity, precip, (empty)
const TILES: TileSpec[] = [
  { layer: 'pm25', label: 'PM2.5', decimals: 0 },
  { layer: 'temperature', label: 'TEMP', decimals: 1 },
  { layer: 'uv', label: 'UV INDEX', decimals: 0 },
  { layer: 'humidity', label: 'HUMIDITY', decimals: 0 },
  { layer: 'precipitation', label: 'PRECIP', unitOverride: 'mm/h', decimals: 1 },
];

const pickStat = (
  climate: RegionClimateOverview | null,
  layer: ClimateLayer,
): RegionClimateStat | null => {
  if (!climate) return null;
  if (climate.primary?.layer === layer) return climate.primary;
  return climate.secondary.find((s) => s.layer === layer) ?? null;
};

const formatValue = (stat: RegionClimateStat | null, decimals: 0 | 1): string => {
  if (!stat || stat.value === undefined || stat.value === null) return '—';
  return decimals === 0 ? `${Math.round(stat.value)}` : stat.value.toFixed(1);
};

export const ClimateMetricsGrid: React.FC<ClimateMetricsGridProps> = ({ climate }) => (
  <View style={styles.grid}>
    {TILES.map((tile) => {
      const stat = pickStat(climate, tile.layer);
      const value = formatValue(stat, tile.decimals);
      const unit = stat ? (tile.unitOverride ?? stat.unit) : null;
      return (
        <View key={tile.layer} style={styles.cell}>
          <MetricTile
            label={tile.label}
            value={value}
            unit={unit}
            riskLevel={stat?.riskLevel}
          />
        </View>
      );
    })}
    {/* Spacer cell for the empty third column in row 2 */}
    <View style={styles.cell} />
  </View>
);

const styles = StyleSheet.create({
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    rowGap: 32,
    columnGap: 12,
  },
  cell: {
    width: '30%',
    flexGrow: 1,
    flexBasis: '30%',
  },
});

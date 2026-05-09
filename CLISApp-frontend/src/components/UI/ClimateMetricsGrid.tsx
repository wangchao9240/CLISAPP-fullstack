import React from 'react';
import { StyleSheet, View } from 'react-native';
import { MetricTile } from './MetricTile';
import { PALETTE, RADII, TABULAR_NUMS } from '../../constants/designTokens';
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

// Row 1: PM2.5, Temp, UV | Row 2: Humidity, Precip, Wind (if available)
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

/**
 * Wind risk category.
 * Thresholds match BoM descriptive wind scale:
 *   Calm   < 20 km/h  — light/variable, negligible hazard
 *   Breezy 20–40 km/h — fresh breeze, minor outdoor impact
 *   Strong > 40 km/h  — strong to gale, elevated outdoor risk
 */
const windRiskLabel = (kmh: number): string => {
  if (kmh < 20) return 'Calm';
  if (kmh <= 40) return 'Breezy';
  return 'Strong';
};

export const ClimateMetricsGrid: React.FC<ClimateMetricsGridProps> = ({ climate }) => {
  const hasWind =
    climate?.wind_speed !== undefined && climate.wind_speed !== null;
  const windKmh = hasWind ? Math.round(climate!.wind_speed as number) : 0;

  // Total rendered cells: 5 standard + 1 (wind or spacer) = always 6
  // Grid is 3 columns × 2 rows.
  // Last row indices (0-based): 3, 4, 5 — no bottom border.
  // Last column positions: index % 3 === 2 — no right border.

  return (
    <View style={styles.grid}>
      {TILES.map((tile, idx) => {
        const stat = pickStat(climate, tile.layer);
        const value = formatValue(stat, tile.decimals);
        const unit = stat ? (tile.unitOverride ?? stat.unit) : null;
        // 3 cols × 2 rows: indices 0-2 = row 1, indices 3-4 = row 2 (standard tiles)
        const isLastCol = idx % 3 === 2;
        // Row 2 starts at index 3; standard tiles 3 & 4 are in last row only if no wind
        const isLastRow = idx >= 3;
        return (
          <View
            key={tile.layer}
            style={[
              styles.cell,
              isLastCol && styles.cellNoRightBorder,
              isLastRow && styles.cellNoBottomBorder,
            ]}
          >
            <MetricTile
              label={tile.label}
              value={value}
              unit={unit}
              riskLevel={stat?.riskLevel}
              tabularNums={TABULAR_NUMS}
            />
          </View>
        );
      })}

      {/* 6th cell: wind tile or spacer — index 5, col 3 (right) + row 2 (bottom) */}
      {hasWind ? (
        <View style={[styles.cell, styles.cellNoRightBorder, styles.cellNoBottomBorder]}>
          <MetricTile
            label="WIND"
            value={`${windKmh}`}
            unit="km/h"
            riskLevel={windRiskLabel(windKmh)}
            tabularNums={TABULAR_NUMS}
          />
        </View>
      ) : (
        <View
          style={[
            styles.cell,
            styles.cellNoRightBorder,
            styles.cellNoBottomBorder,
            styles.cellSpacer,
          ]}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    borderWidth: 1,
    borderColor: PALETTE.border,
    borderRadius: RADII.control,
    overflow: 'hidden',
  },
  cell: {
    width: '33.33%',
    flexBasis: '33.33%',
    flexGrow: 1,
    borderRightWidth: 1,
    borderRightColor: PALETTE.border,
    borderBottomWidth: 1,
    borderBottomColor: PALETTE.border,
    padding: 10,
    minHeight: 78,
  },
  cellNoRightBorder: {
    borderRightWidth: 0,
  },
  cellNoBottomBorder: {
    borderBottomWidth: 0,
  },
  cellSpacer: {
    backgroundColor: PALETTE.surface2,
  },
});

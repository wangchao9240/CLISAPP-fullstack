import React, { useMemo } from 'react';
import { StyleSheet, View, Text } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { PALETTE, RADII, TABULAR_NUMS } from '../../constants/designTokens';
import {
  getClimateDeltaState,
  getDailyBaseline,
  doyFromDate,
} from '../../utils/climateDelta';
import type { RegionClimateOverview } from '../../types/region.types';

interface TodayVsReferenceBandProps {
  regionSscId: string | null;
  climate: RegionClimateOverview | null;
  variant: 'collapsed' | 'expanded';
}

// ── Row tag chip ──────────────────────────────────────────────────────────────

const TagChip: React.FC<{ label: string }> = ({ label }) => (
  <View style={styles.tag}>
    <Text style={styles.tagText}>{label}</Text>
  </View>
);

// ── Marker tile ───────────────────────────────────────────────────────────────

const Marker: React.FC<{ tint: 'cool' | 'warm'; isExpanded: boolean }> = ({
  tint,
  isExpanded,
}) => {
  const bg = tint === 'cool' ? PALETTE.coolSoft : PALETTE.warmSoft;
  const color = tint === 'cool' ? PALETTE.cool : PALETTE.warm;
  const size = isExpanded ? 42 : 36;
  const radius = isExpanded ? 12 : 10;
  const iconName = tint === 'cool' ? 'arrow-down' : 'arrow-up';
  return (
    <View
      style={[
        styles.markerBase,
        { width: size, height: size, borderRadius: radius, backgroundColor: bg },
      ]}
    >
      <Icon name={iconName} size={isExpanded ? 20 : 18} color={color} />
    </View>
  );
};

// ── Individual row ────────────────────────────────────────────────────────────

interface RowProps {
  tint: 'cool' | 'warm';
  valueText: string;
  sourceCaption?: string; // expanded only
  labelText: string;
  metaText?: string; // expanded only
  tagLabel: string;
  isLast: boolean;
  isExpanded: boolean;
}

const RefRow: React.FC<RowProps> = ({
  tint,
  valueText,
  sourceCaption,
  labelText,
  metaText,
  tagLabel,
  isLast,
  isExpanded,
}) => {
  const valueColor = tint === 'cool' ? PALETTE.cool : PALETTE.warm;
  const rowPad = isExpanded
    ? { paddingVertical: 14, paddingHorizontal: 16 }
    : { paddingVertical: 11, paddingHorizontal: 14 };

  return (
    <View
      style={[
        styles.row,
        rowPad,
        !isLast && styles.rowBorderBottom,
      ]}
    >
      <Marker tint={tint} isExpanded={isExpanded} />

      <View style={styles.body}>
        {isExpanded ? (
          <View style={styles.headlineRow}>
            <Text
              style={[styles.valueExpanded, { color: valueColor }]}
              {...TABULAR_NUMS}
            >
              {valueText}
            </Text>
            {sourceCaption ? (
              <Text style={styles.sourceCaption}>{sourceCaption}</Text>
            ) : null}
          </View>
        ) : (
          <Text
            style={[styles.valueCollapsed, { color: valueColor }]}
            {...TABULAR_NUMS}
          >
            {valueText}
          </Text>
        )}
        <Text style={isExpanded ? styles.labelExpanded : styles.labelCollapsed}>
          {labelText}
        </Text>
        {isExpanded && metaText ? (
          <Text style={styles.meta}>{metaText}</Text>
        ) : null}
      </View>

      <TagChip label={tagLabel} />
    </View>
  );
};

// ── Compute MTD rainfall from daily baseline ─────────────────────────────────

const computeTypicalMtdRainfall = (
  regionSscId: string | null,
  today: Date,
): { mmRounded: number; monthName: string } | null => {
  if (!regionSscId) return null;
  const year = today.getFullYear();
  const month = today.getMonth(); // 0-based
  const dayOfMonth = today.getDate();

  // Sum typical daily rf for days 1..dayOfMonth of current month
  let total = 0;
  let hasData = false;
  for (let d = 1; d <= dayOfMonth; d++) {
    const date = new Date(year, month, d);
    const doy = doyFromDate(date);
    const baseline = getDailyBaseline(regionSscId, doy);
    if (baseline?.rf !== undefined) {
      total += baseline.rf;
      hasData = true;
    }
  }
  if (!hasData) return null;

  const monthName = new Intl.DateTimeFormat('en-AU', { month: 'long' }).format(today);
  return { mmRounded: Math.round(total), monthName };
};

// ── Main component ────────────────────────────────────────────────────────────

export const TodayVsReferenceBand: React.FC<TodayVsReferenceBandProps> = ({
  regionSscId,
  climate,
  variant,
}) => {
  const isExpanded = variant === 'expanded';
  const today = useMemo(() => new Date(), []);

  // ── Climate row ───────────────────────────────────────────────────────────
  const deltaState = useMemo(
    () => getClimateDeltaState(regionSscId, climate, today),
    [regionSscId, climate, today],
  );

  const climateAvailable =
    deltaState.variant !== 'unavailable' && deltaState.deltaLabel !== null;

  const climateTint: 'cool' | 'warm' =
    deltaState.variant === 'cool' ? 'cool' : 'warm';

  const climateLabel =
    deltaState.variant === 'cool'
      ? 'Cooler than 1890–1960 baseline'
      : 'Warmer than 1890–1960 baseline';

  // ── Rainfall row ─────────────────────────────────────────────────────────
  const rainfallData = useMemo(
    () => computeTypicalMtdRainfall(regionSscId, today),
    [regionSscId, today],
  );

  const rainfallAvailable = rainfallData !== null;

  // Neither row — render nothing
  if (!climateAvailable && !rainfallAvailable) {
    return null;
  }

  const rows: React.ReactNode[] = [];
  let rowIndex = 0;
  const totalRows =
    (climateAvailable ? 1 : 0) + (rainfallAvailable ? 1 : 0);

  if (climateAvailable) {
    rowIndex++;
    const isLast = rowIndex === totalRows;
    rows.push(
      <RefRow
        key="climate"
        tint={climateTint}
        valueText={deltaState.deltaLabel!}
        sourceCaption={isExpanded ? 'vs 1890–1960' : undefined}
        labelText={climateLabel}
        metaText={isExpanded ? 'Daily mean compared with 70-yr reference period.' : undefined}
        tagLabel="Climate"
        isLast={isLast}
        isExpanded={isExpanded}
      />,
    );
  }

  if (rainfallAvailable) {
    rowIndex++;
    const isLast = rowIndex === totalRows;
    const { mmRounded, monthName } = rainfallData!;
    rows.push(
      <RefRow
        key="rainfall"
        tint="cool"
        valueText={`${mmRounded} mm`}
        sourceCaption={isExpanded ? 'typical MTD' : undefined}
        labelText={`Typical ${monthName} rainfall to date (1890–1960)`}
        metaText={isExpanded ? `Typical ${monthName} rainfall month-to-date: ${mmRounded} mm (1890–1960 baseline).` : undefined}
        tagLabel="Rainfall"
        isLast={isLast}
        isExpanded={isExpanded}
      />,
    );
  }

  return (
    <View style={styles.card}>
      {!isExpanded && (
        <View style={styles.header}>
          <Text style={styles.headerText}>TODAY VS REFERENCE</Text>
        </View>
      )}
      {rows}
    </View>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  card: {
    backgroundColor: PALETTE.surface,
    borderWidth: 1,
    borderColor: PALETTE.border,
    borderRadius: RADII.control,
    overflow: 'hidden',
    marginTop: 14,
  },
  header: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderBottomWidth: 1,
    borderBottomColor: PALETTE.border,
  },
  headerText: {
    fontSize: 10.5,
    fontWeight: '600',
    letterSpacing: 0.84,
    textTransform: 'uppercase',
    color: PALETTE.muted,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  rowBorderBottom: {
    borderBottomWidth: 1,
    borderBottomColor: PALETTE.surface3,
  },
  markerBase: {
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  body: {
    flex: 1,
    minWidth: 0,
  },
  headlineRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 8,
  },
  valueCollapsed: {
    fontSize: 18,
    fontWeight: '600',
    letterSpacing: -0.27,
    lineHeight: 22,
  },
  valueExpanded: {
    fontSize: 22,
    fontWeight: '600',
    letterSpacing: -0.44,
    lineHeight: 24,
  },
  sourceCaption: {
    fontSize: 10,
    fontFamily: undefined, // system mono not reliably available in RN; use default
    letterSpacing: 0.4,
    textTransform: 'uppercase',
    color: PALETTE.faint,
  },
  labelCollapsed: {
    fontSize: 12,
    lineHeight: 16,
    color: PALETTE.muted,
    marginTop: 2,
  },
  labelExpanded: {
    fontSize: 13,
    lineHeight: 18,
    color: PALETTE.fg2,
    marginTop: 2,
  },
  meta: {
    fontSize: 11.5,
    lineHeight: 16,
    color: PALETTE.muted,
    marginTop: 4,
  },
  tag: {
    backgroundColor: PALETTE.surface3,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    alignSelf: 'flex-start',
    flexShrink: 0,
  },
  tagText: {
    fontSize: 9.5,
    fontWeight: '600',
    letterSpacing: 0.76,
    textTransform: 'uppercase',
    color: PALETTE.fg2,
  },
});

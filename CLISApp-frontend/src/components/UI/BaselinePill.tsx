// CLISApp-frontend/src/components/UI/BaselinePill.tsx
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { DELTA_COLORS, HEALTH_SHEET_COLORS } from '../../constants/healthDesignTokens';
import { getClimateDeltaState, ClimateDeltaVariant } from '../../utils/climateDelta';
import type { RegionClimateOverview } from '../../types/region.types';

interface BaselinePillProps {
  regionSscId: string | null;
  climate: RegionClimateOverview | null;
}

const VARIANT_COLOR: Record<ClimateDeltaVariant, string> = {
  warm: DELTA_COLORS.warm,
  cool: DELTA_COLORS.cool,
  neutral: DELTA_COLORS.neutral,
  unavailable: DELTA_COLORS.neutral,
};

export const BaselinePill: React.FC<BaselinePillProps> = ({ regionSscId, climate }) => {
  const state = getClimateDeltaState(regionSscId, climate);
  const deltaColor = VARIANT_COLOR[state.variant];

  return (
    <View
      style={styles.pill}
      accessibilityRole="text"
      accessibilityLabel={
        state.deltaLabel
          ? `${state.deltaLabel} ${state.subtitleText.toLowerCase()}`
          : state.subtitleText.toLowerCase()
      }
    >
      {state.deltaLabel ? (
        <Text style={[styles.delta, { color: deltaColor }]}>{state.deltaLabel}</Text>
      ) : null}
      <Text style={styles.subtitle}>{state.subtitleText}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: HEALTH_SHEET_COLORS.surfaceContainerLow,
  },
  delta: {
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: -0.4,
  },
  subtitle: {
    fontSize: 9,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: HEALTH_SHEET_COLORS.outline,
  },
});

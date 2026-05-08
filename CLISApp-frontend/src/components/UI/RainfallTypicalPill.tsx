// CLISApp-frontend/src/components/UI/RainfallTypicalPill.tsx
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import {
  DELTA_COLORS,
  HEALTH_SHEET_COLORS,
} from '../../constants/healthDesignTokens';
import {
  doyFromDate,
  formatDailyBaselineDateLabel,
  getDailyBaseline,
} from '../../utils/climateDelta';

interface RainfallTypicalPillProps {
  regionSscId: string | null;
}

export const RainfallTypicalPill: React.FC<RainfallTypicalPillProps> = ({
  regionSscId,
}) => {
  const date = new Date();
  const label = formatDailyBaselineDateLabel(date);
  const dailyBaseline = getDailyBaseline(regionSscId, doyFromDate(date));
  const rainfall = dailyBaseline?.rf;

  if (rainfall === undefined) {
    return null;
  }

  const subtitleText = `TYPICAL ${label.toUpperCase()} RAINFALL (1890-1960)`;
  const valueText = `${rainfall.toFixed(1)} mm`;

  return (
    <View
      style={styles.pill}
      accessibilityRole="text"
      accessibilityLabel={`Typical ${label} rainfall: ${valueText}`}
    >
      <Text style={styles.value}>{valueText}</Text>
      <Text style={styles.subtitle}>{subtitleText}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: HEALTH_SHEET_COLORS.surfaceContainerLow,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(100, 181, 246, 0.32)',
  },
  value: {
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 0,
    color: DELTA_COLORS.cool,
  },
  subtitle: {
    fontSize: 9,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: HEALTH_SHEET_COLORS.outline,
  },
});

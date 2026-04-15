import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { HEALTH_SHEET_COLORS, RISK_TEXT_COLORS, RiskKey } from '../../constants/healthDesignTokens';

interface MetricTileProps {
  label: string;
  value: string;
  unit: string | null;
  riskLevel: string | undefined;
}

const toRiskKey = (risk: string | undefined): RiskKey => {
  if (risk && (risk in RISK_TEXT_COLORS)) return risk as RiskKey;
  return 'Unknown';
};

const riskDisplayText = (risk: string | undefined): string => {
  const key = toRiskKey(risk);
  return key === 'Unknown' ? '—' : key.toUpperCase();
};

export const MetricTile: React.FC<MetricTileProps> = ({ label, value, unit, riskLevel }) => {
  const riskKey = toRiskKey(riskLevel);
  const riskColor = RISK_TEXT_COLORS[riskKey];
  const riskText = riskDisplayText(riskLevel);

  return (
    <View
      style={styles.tile}
      accessibilityRole="text"
      accessibilityLabel={`${label}: ${value}${unit ? ` ${unit}` : ''}, ${riskKey}`}
    >
      <Text style={styles.label} numberOfLines={1}>{label}</Text>
      <View style={styles.valueRow}>
        <Text style={styles.value}>{value}</Text>
        {unit ? <Text style={styles.unit}>{unit}</Text> : null}
      </View>
      <Text style={[styles.risk, { color: riskColor }]}>{riskText}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    minWidth: 0,
  },
  label: {
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    color: HEALTH_SHEET_COLORS.outline,
    marginBottom: 4,
  },
  valueRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  value: {
    fontSize: 24,
    fontWeight: '700',
    color: HEALTH_SHEET_COLORS.onSurface,
    letterSpacing: -0.4,
    lineHeight: 24,
  },
  unit: {
    fontSize: 11,
    fontWeight: '500',
    color: HEALTH_SHEET_COLORS.onSurfaceVariant,
    marginLeft: 2,
  },
  risk: {
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
    marginTop: 6,
  },
});

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { HealthRiskLevel } from '../../types/climate.types';

export interface HealthRiskBadgeProps {
  riskLevel?: string;
  adviceText?: string;
  testID?: string;
  accessibilityLabel?: string;
}

interface RiskLevelVisual {
  bg: string;
  text: string;
  icon: string;
  label: string;
}

export const RISK_LEVEL_VISUALS: Record<
  HealthRiskLevel | 'Unknown',
  RiskLevelVisual
> = {
  Good: {
    bg: '#66BB6A',
    text: '#FFFFFF',
    icon: 'check-circle',
    label: 'Good',
  },
  Moderate: {
    bg: '#FDD835',
    text: '#5C4B00',
    icon: 'alert-circle-outline',
    label: 'Moderate',
  },
  Unhealthy: {
    bg: '#FF8A65',
    text: '#FFFFFF',
    icon: 'alert',
    label: 'Unhealthy',
  },
  Hazardous: {
    bg: '#E57373',
    text: '#FFFFFF',
    icon: 'alert-octagon',
    label: 'Hazardous',
  },
  Unknown: {
    bg: '#E0E2EA',
    text: '#414752',
    icon: 'help-circle-outline',
    label: 'Unknown',
  },
};

const getRiskLevelVisual = (riskLevel?: string): RiskLevelVisual => {
  if (!riskLevel) {
    return RISK_LEVEL_VISUALS.Unknown;
  }

  return RISK_LEVEL_VISUALS[riskLevel as keyof typeof RISK_LEVEL_VISUALS] ?? RISK_LEVEL_VISUALS.Unknown;
};

export const HealthRiskBadge: React.FC<HealthRiskBadgeProps> = ({
  riskLevel,
  adviceText,
  testID,
  accessibilityLabel,
}) => {
  const visual = getRiskLevelVisual(riskLevel);
  // Only append advice when risk is known — avoids misleading screen-reader
  // announcements like "Unknown air/health risk. Health guidance unavailable…"
  // during the loading/empty state.
  const defaultAccessibilityLabel =
    adviceText && visual.label !== 'Unknown'
      ? `${visual.label} air/health risk. ${adviceText}`
      : `${visual.label} air/health risk`;

  return (
    <View
      testID={testID}
      style={[styles.badge, { backgroundColor: visual.bg }]}
      accessibilityRole="text"
      accessibilityLabel={accessibilityLabel ?? defaultAccessibilityLabel}
    >
      <Icon
        name={visual.icon}
        size={16}
        color={visual.text}
        accessible={false}
        accessibilityElementsHidden={true}
        importantForAccessibility="no"
      />
      <Text style={[styles.label, { color: visual.text }]}>{visual.label}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 16,
    alignSelf: 'flex-start',
  },
  label: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: -0.2,
  },
});

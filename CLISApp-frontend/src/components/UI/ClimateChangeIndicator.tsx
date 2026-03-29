import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import climateBaseline from '../../../assets/data/climate_baseline.json';
import { getActiveClimateStat } from '../../constants/climateData';
import { RegionClimateOverview } from '../../types/region.types';

interface ClimateChangeIndicatorProps {
  regionSscId: string | null;
  climate: RegionClimateOverview | null;
}

const BASELINE_THRESHOLD = 0.1;
const FALLBACK_MESSAGE = 'Baseline data not available for this region';
const TITLE = 'Climate Change Indicator';
const baselineData = climateBaseline as {
  baselines: Record<string, { bmT?: number }>;
};

const VARIANT_COLORS = {
  warm: '#FF7043',
  cool: '#81D4FA',
  neutral: '#78909C',
} as const;

const formatDiff = (diff: number): string => `${diff > 0 ? '+' : ''}${diff.toFixed(1)}°C`;

const getIndicatorState = (regionSscId: string | null, climate: RegionClimateOverview | null) => {
  if (!regionSscId) {
    return {
      iconName: null,
      iconColor: null,
      valueText: null,
      subtitleText: FALLBACK_MESSAGE,
    };
  }

  const baselineTemperature = baselineData.baselines[regionSscId]?.bmT;
  const currentTemperature = getActiveClimateStat(climate, 'temperature')?.value;

  if (baselineTemperature === undefined || currentTemperature === undefined) {
    return {
      iconName: null,
      iconColor: null,
      valueText: null,
      subtitleText: FALLBACK_MESSAGE,
    };
  }

  const diff = currentTemperature - baselineTemperature;

  if (diff > BASELINE_THRESHOLD) {
    return {
      iconName: 'arrow-top-right',
      iconColor: VARIANT_COLORS.warm,
      valueText: formatDiff(diff),
      subtitleText: 'above 1890-1960 baseline',
    };
  }

  if (diff < -BASELINE_THRESHOLD) {
    return {
      iconName: 'arrow-bottom-right',
      iconColor: VARIANT_COLORS.cool,
      valueText: formatDiff(diff),
      subtitleText: 'below 1890-1960 baseline',
    };
  }

  return {
    iconName: 'approximately-equal',
    iconColor: VARIANT_COLORS.neutral,
    valueText: null,
    subtitleText: 'Near 1890-1960 baseline',
  };
};

export const ClimateChangeIndicator: React.FC<ClimateChangeIndicatorProps> = ({
  regionSscId,
  climate,
}) => {
  const indicatorState = getIndicatorState(regionSscId, climate);

  return (
    <View style={styles.climateCard}>
      <View style={styles.climateCardHeader}>
        <Icon name="thermometer" size={16} color="#005dac" />
        <Text style={styles.climateCardTitle}>{TITLE}</Text>
      </View>
      {indicatorState.iconName ? (
        <View style={styles.climateCardValueContainer}>
          <Icon
            name={indicatorState.iconName}
            size={24}
            color={indicatorState.iconColor ?? undefined}
          />
          {indicatorState.valueText ? (
            <Text style={[styles.climateCardValue, { color: indicatorState.iconColor ?? undefined }]}>
              {indicatorState.valueText}
            </Text>
          ) : null}
        </View>
      ) : null}
      <Text style={styles.climateCardSubtitle}>{indicatorState.subtitleText}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  climateCard: {
    backgroundColor: '#F2F3FC',
    borderRadius: 16,
    padding: 16,
    marginBottom: 24,
  },
  climateCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  climateCardTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#414752',
    textTransform: 'uppercase',
    letterSpacing: -0.2,
  },
  climateCardValueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 8,
  },
  climateCardValue: {
    fontSize: 24,
    fontWeight: '900',
    letterSpacing: -1,
  },
  climateCardSubtitle: {
    fontSize: 12,
    fontWeight: '500',
    color: '#717783',
    marginTop: 4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
});

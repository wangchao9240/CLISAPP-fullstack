import React, { useRef } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Swipeable } from 'react-native-gesture-handler';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { getActiveClimateStat } from '../../constants/climateData';
import {
  CATEGORY_BADGE_COLORS,
  DEFAULT_BADGE_COLORS,
} from '../../constants/healthColors';
import type { FavoriteLocation } from '../../store/favoritesStore';
import type { RegionClimateOverview } from '../../types/region.types';
import { getIndicatorState } from './ClimateChangeIndicator';

interface FavoriteLocationCardProps {
  favorite: FavoriteLocation;
  climate: RegionClimateOverview | null;
  isClimateLoading: boolean;
  onPress: () => void;
  onDelete: () => void;
}

const formatRelativeTime = (isoTimestamp: string): string => {
  const saved = new Date(isoTimestamp).getTime();
  const now = Date.now();
  const diffMs = now - saved;

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;

  return new Date(isoTimestamp).toLocaleDateString();
};

const renderRightActions = (onDelete: () => void, regionName: string) => (
  <Pressable
    onPress={onDelete}
    style={styles.deleteAction}
    accessibilityRole="button"
    accessibilityLabel={`Delete favorite ${regionName}`}
  >
    <Icon name="delete" size={24} color="#FFFFFF" />
    <Text style={styles.deleteText}>Delete</Text>
  </Pressable>
);

export const FavoriteLocationCard: React.FC<FavoriteLocationCardProps> = ({
  favorite,
  climate,
  isClimateLoading,
  onPress,
  onDelete,
}) => {
  const swipeableRef = useRef<Swipeable>(null);
  const tempStat = getActiveClimateStat(climate, 'temperature');
  const category = tempStat?.category ?? null;
  const badgeColors = category
    ? CATEGORY_BADGE_COLORS[category] ?? DEFAULT_BADGE_COLORS
    : DEFAULT_BADGE_COLORS;
  const indicatorState = getIndicatorState(favorite.regionId, climate);
  const healthLabel = isClimateLoading ? 'Loading...' : category ?? 'No data';
  const { iconName, iconColor, valueText } = indicatorState;
  const hasDelta = iconName != null && iconColor != null && valueText != null;

  const handleDelete = () => {
    swipeableRef.current?.close();
    onDelete();
  };

  return (
    <Swipeable
      ref={swipeableRef}
      renderRightActions={() => renderRightActions(handleDelete, favorite.regionName)}
      overshootRight={false}
      friction={2}
    >
      <Pressable
        onPress={onPress}
        style={styles.card}
        accessibilityRole="button"
        accessibilityLabel={`View ${favorite.regionName} on map`}
      >
        <View style={styles.leftContent}>
          <Text style={styles.regionName} numberOfLines={1}>
            {favorite.regionName}
          </Text>
          <View style={styles.metaRow}>
            <View
              style={[
                styles.healthDot,
                {
                  backgroundColor: isClimateLoading
                    ? '#BDBDBD'
                    : badgeColors.dot,
                },
              ]}
            />
            <Text style={styles.healthLabel}>{healthLabel}</Text>
            {tempStat ? (
              <>
                <View style={styles.separatorDot} />
                <Text style={styles.metaText}>
                  {`${tempStat.value} ${tempStat.unit}`}
                </Text>
              </>
            ) : null}
            <View style={styles.separatorDot} />
            <Text style={styles.metaText}>
              {formatRelativeTime(favorite.timestamp)}
            </Text>
          </View>
        </View>
        <View style={styles.rightContent}>
          {hasDelta ? (
            <View style={styles.deltaContainer}>
              <Icon name={iconName} size={14} color={iconColor} />
              <Text style={[styles.deltaText, { color: iconColor }]}>
                {valueText}
              </Text>
            </View>
          ) : null}
          <Icon name="chevron-right" size={16} color="#BDBDBD" />
        </View>
      </Pressable>
    </Swipeable>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    minHeight: 88,
    marginHorizontal: 16,
    marginVertical: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 1,
    borderWidth: 1,
    borderColor: 'rgba(193, 198, 212, 0.3)',
  },
  leftContent: {
    flex: 1,
    flexDirection: 'column',
    gap: 8,
  },
  regionName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#181C21',
    lineHeight: 20,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  healthDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#BDBDBD',
  },
  healthLabel: {
    fontSize: 11,
    fontWeight: '500',
    color: '#717783',
  },
  separatorDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#717783',
  },
  metaText: {
    fontSize: 14,
    color: '#414752',
  },
  rightContent: {
    flexDirection: 'column',
    alignItems: 'flex-end',
    justifyContent: 'center',
    paddingLeft: 8,
  },
  deltaContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    marginBottom: 4,
  },
  deltaText: {
    fontSize: 14,
    fontWeight: '500',
  },
  deleteAction: {
    backgroundColor: '#E57373',
    justifyContent: 'center',
    alignItems: 'center',
    width: 80,
    flexDirection: 'column',
    gap: 4,
    borderTopRightRadius: 12,
    borderBottomRightRadius: 12,
    marginVertical: 4,
  },
  deleteText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#FFFFFF',
  },
});

import React, { useRef } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { Swipeable } from 'react-native-gesture-handler';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { getActiveClimateStat } from '../../constants/climateData';
import {
  CATEGORY_BADGE_COLORS,
  DEFAULT_BADGE_COLORS,
} from '../../constants/healthColors';
import { PALETTE, RADII, TABULAR_NUMS } from '../../constants/designTokens';
import type { FavoriteLocation } from '../../store/favoritesStore';
import type { RegionClimateOverview } from '../../types/region.types';
import { getClimateDeltaState } from '../../utils/climateDelta';

// Maps delta variant to icon name and text/bg colour tokens.
const VARIANT_ICONS: Record<
  string,
  { iconName: string; textColor: string; bgColor: string }
> = {
  warm: {
    iconName: 'arrow-top-right',
    textColor: PALETTE.warm,
    bgColor: PALETTE.warmSoft,
  },
  cool: {
    iconName: 'arrow-bottom-right',
    textColor: PALETTE.cool,
    bgColor: PALETTE.coolSoft,
  },
  neutral: {
    iconName: 'approximately-equal',
    textColor: PALETTE.muted,
    bgColor: PALETTE.surface3,
  },
};

interface FavoriteLocationCardProps {
  favorite: FavoriteLocation;
  climate: RegionClimateOverview | null;
  isClimateLoading: boolean;
  onPress: () => void;
  onDelete: () => void;
}

// Format timestamp as "31 Mar 2026".
const formatDate = (isoTimestamp: string): string =>
  new Date(isoTimestamp).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

// Build the tag line shown under the region name.
// Falls back gracefully when regionId lacks the expected SSC suffix.
const buildTagLine = (favorite: FavoriteLocation): string => {
  const sscMatch = favorite.regionId.match(/ssc[- _]?(\d+)/i);
  const sscPart = sscMatch ? `SSC ${sscMatch[1]}` : favorite.regionId;
  return `QLD · ${sscPart}`;
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

  const deltaState = getClimateDeltaState(favorite.regionId, climate);
  const variantInfo =
    deltaState.variant !== 'unavailable'
      ? (VARIANT_ICONS[deltaState.variant] ?? null)
      : null;

  // Only show delta chip when there is a label (neutral has no label).
  const hasDelta =
    variantInfo != null && deltaState.deltaLabel != null;

  const riskLabel = isClimateLoading ? 'Loading...' : (category ?? 'No data');
  const dotColor = isClimateLoading ? PALETTE.faint : badgeColors.dot;

  const handleDelete = () => {
    swipeableRef.current?.close();
    onDelete();
  };

  return (
    <Swipeable
      ref={swipeableRef}
      renderRightActions={() =>
        renderRightActions(handleDelete, favorite.regionName)
      }
      overshootRight={false}
      friction={2}
    >
      <Pressable
        onPress={onPress}
        style={styles.card}
        accessibilityRole="button"
        accessibilityLabel={`View ${favorite.regionName} on map`}
      >
        {/* Top row: name + tag on left, delta chip on right */}
        <View style={styles.topRow}>
          <View style={styles.nameBlock}>
            <Text style={styles.regionName} numberOfLines={1}>
              {favorite.regionName}
            </Text>
            <Text style={styles.tagLine} numberOfLines={1}>
              {buildTagLine(favorite)}
            </Text>
          </View>

          {hasDelta && variantInfo ? (
            <View
              style={[
                styles.deltaChip,
                { backgroundColor: variantInfo.bgColor },
              ]}
            >
              <Icon
                name={variantInfo.iconName}
                size={14}
                color={variantInfo.textColor}
              />
              <Text
                style={[styles.deltaValue, { color: variantInfo.textColor }]}
                {...TABULAR_NUMS}
              >
                {deltaState.deltaLabel}
              </Text>
            </View>
          ) : null}
        </View>

        {/* Bottom row: risk dot + level · temp · date + chevron */}
        <View style={styles.bottomRow}>
          <View
            style={[styles.riskDot, { backgroundColor: dotColor }]}
          />
          <Text style={styles.riskLevel}>{riskLabel}</Text>

          {tempStat ? (
            <>
              <View style={styles.sepDot} />
              <Text style={styles.tempText} {...TABULAR_NUMS}>
                {`${tempStat.value} °C`}
              </Text>
            </>
          ) : null}

          <View style={styles.sepDot} />
          <Text style={styles.dateText} {...TABULAR_NUMS}>
            {formatDate(favorite.timestamp)}
          </Text>

          <Icon
            name="chevron-right"
            size={14}
            color={PALETTE.faint}
            style={styles.chevron}
          />
        </View>
      </Pressable>
    </Swipeable>
  );
};

const cardShadow = Platform.select({
  ios: {
    shadowColor: '#0D1220',
    shadowOpacity: 0.04,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 2,
  },
  android: {},
  default: {},
});

const styles = StyleSheet.create({
  card: {
    backgroundColor: PALETTE.surface,
    borderRadius: RADII.card,
    borderWidth: 1,
    borderColor: PALETTE.border,
    padding: 18,
    marginVertical: 6,
    marginHorizontal: 14,
    gap: 14,
    ...cardShadow,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
  },
  nameBlock: {
    flex: 1,
  },
  regionName: {
    fontSize: 22,
    fontWeight: '700',
    color: PALETTE.fg,
    letterSpacing: -0.44,
    lineHeight: 24,
  },
  tagLine: {
    fontSize: 10.5,
    fontWeight: '600',
    letterSpacing: 0.63,
    textTransform: 'uppercase',
    color: PALETTE.muted,
    marginTop: 5,
  },
  deltaChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 7,
    paddingHorizontal: 11,
    borderRadius: 10,
    flexShrink: 0,
  },
  deltaValue: {
    fontSize: 21,
    fontWeight: '600',
    letterSpacing: -0.42,
  },
  bottomRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  riskDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  riskLevel: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.66,
    textTransform: 'uppercase',
    color: PALETTE.muted,
  },
  sepDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: PALETTE.faint,
    marginHorizontal: 6,
  },
  tempText: {
    fontSize: 13,
    fontWeight: '500',
    letterSpacing: -0.065,
    color: PALETTE.fg2,
  },
  dateText: {
    fontSize: 11.5,
    letterSpacing: 0.23,
    color: PALETTE.faint,
    fontFamily: 'Menlo',
  },
  chevron: {
    marginLeft: 'auto',
  },
  deleteAction: {
    backgroundColor: '#E57373',
    justifyContent: 'center',
    alignItems: 'center',
    width: 80,
    flexDirection: 'column',
    gap: 4,
    borderTopRightRadius: RADII.card,
    borderBottomRightRadius: RADII.card,
    marginVertical: 6,
  },
  deleteText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#FFFFFF',
  },
});

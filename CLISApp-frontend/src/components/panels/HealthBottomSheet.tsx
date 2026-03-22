import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import { StyleSheet, View, Text, Pressable, Platform } from 'react-native';
import {
  BottomSheetModal,
  BottomSheetView,
  BottomSheetScrollView,
  BottomSheetBackdrop,
} from '@gorhom/bottom-sheet';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { formatBadgeText, getActiveClimateStat } from '../../constants/climateData';
import { useMapStore } from '../../store/mapStore';
import { useFavoritesStore } from '../../store/favoritesStore';

const SNAP_POINTS = ['40%', '60%', '85%'];
const CATEGORY_BADGE_COLORS: Record<string, { bg: string; text: string }> = {
  'Very Low': { bg: '#C8E6C9', text: '#1B5E20' },
  Low: { bg: '#DCEDC8', text: '#33691E' },
  Moderate: { bg: '#FFDBC7', text: '#733600' },
  High: { bg: '#FFCCBC', text: '#BF360C' },
  'Very High': { bg: '#FFCDD2', text: '#B71C1C' },
};
const DEFAULT_BADGE_COLORS = { bg: '#FFDBC7', text: '#733600' };

export const HealthBottomSheet: React.FC = () => {
  const bottomSheetRef = useRef<BottomSheetModal>(null);

  const {
    regionInfo,
    activeLayer,
    closeRegionInfo,
  } = useMapStore();

  const { isFavorite, addFavorite, removeFavorite } = useFavoritesStore();

  const snapPoints = useMemo(() => SNAP_POINTS, []);
  const activeStat = getActiveClimateStat(regionInfo.climate, activeLayer);
  const badgeColors = CATEGORY_BADGE_COLORS[activeStat?.category ?? ''] ?? DEFAULT_BADGE_COLORS;

  // Sync visibility with store
  useEffect(() => {
    if (regionInfo.visible) {
      bottomSheetRef.current?.present();
    } else {
      bottomSheetRef.current?.dismiss();
    }
  }, [regionInfo.visible]);

  const handleSheetChanges = useCallback(
    (index: number) => {
      if (index === -1 && regionInfo.visible) {
        closeRegionInfo();
      }
    },
    [regionInfo.visible, closeRegionInfo]
  );

  const handleFavoriteToggle = () => {
    if (!regionInfo.regionId || !regionInfo.regionName || !regionInfo.regionType) return;

    // Validate regionType matches favoritesStore contract
    const validTypes = ['lga', 'suburb'] as const;
    const regionType = regionInfo.regionType as string;
    if (!validTypes.includes(regionType as any)) {
      return; // Skip saving if regionType is not supported
    }

    if (isFavorite(regionInfo.regionId)) {
      removeFavorite(regionInfo.regionId);
    } else {
      addFavorite({
        regionId: regionInfo.regionId,
        regionName: regionInfo.regionName,
        regionType: regionType as 'lga' | 'suburb',
        timestamp: new Date().toISOString(),
      });
    }
  };

  // Check if current region type supports favorites
  const canFavorite = regionInfo.regionType === 'lga' || regionInfo.regionType === 'suburb';
  const isFav = regionInfo.regionId && canFavorite ? isFavorite(regionInfo.regionId) : false;

  const renderBackdrop = useCallback(
    (props: any) => (
      <BottomSheetBackdrop
        {...props}
        opacity={0}
        appearsOnIndex={0}
        disappearsOnIndex={-1}
        pressBehavior="close"
      />
    ),
    []
  );

  return (
    <BottomSheetModal
      ref={bottomSheetRef}
      index={0}
      snapPoints={snapPoints}
      onChange={handleSheetChanges}
      enablePanDownToClose={true}
      backdropComponent={renderBackdrop}
      backgroundStyle={styles.sheetBackground}
      handleIndicatorStyle={styles.dragHandle}
    >
      <BottomSheetScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header Row */}
        <View style={styles.headerRow}>
          <View style={styles.titleContainer}>
            <Text style={styles.regionName}>
              {regionInfo.regionName || 'Selected Region'}
            </Text>
            <Pressable onPress={handleFavoriteToggle} style={styles.favoriteButton} disabled={!canFavorite}>
              <Icon
                name={isFav ? 'cards-heart' : 'cards-heart-outline'}
                size={24}
                color={isFav ? '#ba1a1a' : canFavorite ? '#414752' : '#C1C6D4'}
              />
            </Pressable>
          </View>
          <View style={[styles.riskBadge, { backgroundColor: badgeColors.bg }]}>
            <Text style={[styles.riskBadgeText, { color: badgeColors.text }]}>
              {formatBadgeText(activeStat?.value, activeStat?.unit, activeStat?.category, activeLayer)}
            </Text>
          </View>
        </View>

        {/* Health Advice Placeholder */}
        <View style={styles.adviceContainer}>
          <Text style={styles.adviceText}>
            Sensitive groups should reduce prolonged outdoor exertion today.
          </Text>
        </View>

        <View style={styles.divider} />

        {/* Half Level Content - Climate Change Indicator */}
        <View style={styles.climateCard}>
          <View style={styles.climateCardHeader}>
            <Icon name="thermometer" size={16} color="#005dac" />
            <Text style={styles.climateCardTitle}>Climate Change Indicator</Text>
          </View>
          <View style={styles.climateCardValueContainer}>
            <Icon name="arrow-top-right" size={24} color="#FF7043" />
            <Text style={styles.climateCardValue}>+0.4°C</Text>
          </View>
          <Text style={styles.climateCardSubtitle}>above 1890-1960 baseline</Text>
        </View>

        {/* Current Layer Data Section */}
        <View style={styles.layerDataCard}>
          <View style={styles.layerDataHeader}>
            <Text style={styles.layerDataTitle}>
              {activeLayer === 'pm25' ? 'PM2.5' :
               activeLayer === 'uv' ? 'UV' :
               activeLayer === 'temperature' ? 'Temperature' :
               activeLayer === 'humidity' ? 'Humidity' :
               activeLayer === 'precipitation' ? 'Precipitation' : 'Layer'} Details
            </Text>
            <Text style={styles.layerDataValue}>35 ug/m3</Text>
          </View>
          
          <View style={styles.layerDataRow}>
            <Text style={styles.layerDataLabel}>Daily average</Text>
            <Text style={styles.layerDataSubValue}>28 ug/m3</Text>
          </View>
          <View style={styles.layerDataRow}>
            <Text style={styles.layerDataLabel}>Peak today</Text>
            <Text style={styles.layerDataSubValue}>42 ug/m3</Text>
          </View>
          <View style={styles.progressBarContainer}>
            <View style={[styles.progressBarFill, { width: '65%' }]} />
          </View>
        </View>

        <View style={styles.dividerLarge} />

        {/* Full Level Content - Health Impact Data */}
        <View style={styles.impactSection}>
          <View style={styles.impactSectionHeader}>
            <Icon name="google-analytics" size={20} color="#005dac" />
            <Text style={styles.impactSectionTitle}>Health Impact Data</Text>
          </View>

          {/* Respiratory Hospitalizations Card */}
          <View style={styles.impactCard}>
            <View style={styles.impactCardTop}>
              <View style={styles.impactCardTitleContainer}>
                <View style={[styles.iconCircle, { backgroundColor: '#E573731A' }]}>
                  <Icon name="lungs" size={20} color="#E57373" />
                </View>
                <Text style={styles.impactCardTitle}>Respiratory{'\n'}Hospitalizations</Text>
              </View>
              <View style={[styles.statusBadge, { backgroundColor: '#FF8A651A' }]}>
                <Icon name="arrow-up" size={12} color="#FF8A65" />
                <Text style={[styles.statusBadgeText, { color: '#FF8A65' }]}>Elevated</Text>
              </View>
            </View>
            <Text style={styles.impactCardText}>
              PM2.5 levels of 35 ug/m3 correlate with <Text style={styles.textBold}>15% higher</Text> respiratory admission rates.
            </Text>
          </View>

          {/* Cardiovascular Hospitalizations Card */}
          <View style={styles.impactCard}>
            <View style={styles.impactCardTop}>
              <View style={styles.impactCardTitleContainer}>
                <View style={[styles.iconCircle, { backgroundColor: '#E573731A' }]}>
                  <Icon name="heart-pulse" size={20} color="#E57373" />
                </View>
                <Text style={styles.impactCardTitle}>Cardiovascular{'\n'}Hospitalizations</Text>
              </View>
              <View style={[styles.statusBadge, { backgroundColor: '#FDD8351A' }]}>
                <Icon name="minus" size={12} color="#FDD835" />
                <Text style={[styles.statusBadgeText, { color: '#FDD835' }]}>Moderate</Text>
              </View>
            </View>
            <Text style={styles.impactCardText}>
              Current levels associated with marginally elevated cardiovascular risk factors.
            </Text>
          </View>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>Data source: Open-Meteo API | Aggregated health data</Text>
          <Text style={[styles.footerText, styles.footerTextBold]}>Last updated: 2 hours ago</Text>
        </View>
      </BottomSheetScrollView>
    </BottomSheetModal>
  );
};

const styles = StyleSheet.create({
  sheetBackground: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    ...Platform.select({
      ios: {
        shadowColor: '#001C3A',
        shadowOffset: { width: 0, height: -8 },
        shadowOpacity: 0.06,
        shadowRadius: 32,
      },
      android: {
        elevation: 16,
      },
    }),
  },
  dragHandle: {
    width: 32,
    height: 4,
    backgroundColor: '#C1C6D4',
    borderRadius: 2,
    marginTop: 8,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingBottom: 40,
  },
  headerRow: {
    paddingTop: 8,
    gap: 12,
    marginBottom: 12,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  regionName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#181C21',
    letterSpacing: -0.5,
  },
  favoriteButton: {
    padding: 4,
  },
  riskBadge: {
    backgroundColor: '#FFDBC7',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 16,
    alignSelf: 'flex-start',
  },
  riskBadgeText: {
    color: '#733600',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: -0.2,
  },
  adviceContainer: {
    backgroundColor: '#F2F3FC',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
  },
  adviceText: {
    fontSize: 16,
    lineHeight: 24,
    color: '#414752',
    fontWeight: '500',
  },
  divider: {
    height: 1,
    backgroundColor: 'rgba(193, 198, 212, 0.3)',
    marginBottom: 24,
  },
  dividerLarge: {
    height: 1,
    backgroundColor: 'rgba(193, 198, 212, 0.2)',
    marginVertical: 32,
  },
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
    color: '#FF7043',
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
  layerDataCard: {
    backgroundColor: '#F9F9FF', // surface - tonal layering instead of border
    borderRadius: 12,
    padding: 20,
  },
  layerDataHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  layerDataTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#181C21',
  },
  layerDataValue: {
    fontSize: 16,
    fontWeight: '500',
    color: '#005dac',
  },
  layerDataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  layerDataLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#717783',
  },
  layerDataSubValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#414752',
  },
  progressBarContainer: {
    width: '100%',
    height: 8,
    backgroundColor: '#E0E2EA',
    borderRadius: 4,
    overflow: 'hidden',
    marginTop: 8,
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#944700',
  },
  impactSection: {
    gap: 16,
  },
  impactSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  impactSectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#181C21',
  },
  impactCard: {
    backgroundColor: '#F9F9FF', // surface - tonal layering instead of border
    borderRadius: 16,
    padding: 20,
    gap: 16,
  },
  impactCardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  impactCardTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  impactCardTitle: {
    fontWeight: '700',
    color: '#181C21',
    lineHeight: 20,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusBadgeText: {
    fontSize: 12,
    fontWeight: '700',
  },
  impactCardText: {
    fontSize: 14,
    color: '#414752',
    lineHeight: 22,
  },
  textBold: {
    fontWeight: '700',
    color: '#181C21',
  },
  footer: {
    marginTop: 32,
    paddingTop: 16,
    gap: 4,
  },
  footerText: {
    fontSize: 11,
    color: '#717783',
    lineHeight: 14,
  },
  footerTextBold: {
    fontWeight: '500',
  },
});

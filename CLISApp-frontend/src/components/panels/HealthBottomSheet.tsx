import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Animated, StyleSheet, View, Text, Pressable, Platform } from 'react-native';
import {
  BottomSheetModal,
  BottomSheetScrollView,
  BottomSheetBackdrop,
} from '@gorhom/bottom-sheet';
import { Snackbar } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { formatTimeAgo } from '../../utils/formatTimeAgo';
import { getActiveClimateStat } from '../../constants/climateData';
import { getWorstRiskStat } from '../../utils/riskPriority';
import { BaselinePill } from '../UI/BaselinePill';
import { ClimateMetricsGrid } from '../UI/ClimateMetricsGrid';
import {
  HEALTH_SHEET_COLORS,
  IMPACT_COLORS,
} from '../../constants/healthDesignTokens';
import { useMapStore } from '../../store/mapStore';
import { FavoriteLocation, useFavoritesStore } from '../../store/favoritesStore';

const SNAP_POINTS = ['40%', '60%', '85%'];
const DEFAULT_ADVICE_FALLBACK = 'Conditions are within expected ranges.';

export const HealthBottomSheet: React.FC = () => {
  const bottomSheetRef = useRef<BottomSheetModal>(null);
  const heartScale = useRef(new Animated.Value(1)).current;
  const [deletedFavorite, setDeletedFavorite] = useState<FavoriteLocation | null>(null);
  const [isSnackbarVisible, setIsSnackbarVisible] = useState(false);

  const { regionInfo, activeLayer, closeRegionInfo, clearRegionInfo } = useMapStore();

  const { isFavorite, addFavorite, restoreFavorite, removeFavorite, getFavorite } =
    useFavoritesStore();

  const snapPoints = useMemo(() => SNAP_POINTS, []);

  const worstRisk = getWorstRiskStat(regionInfo.climate);
  const activeStat = getActiveClimateStat(regionInfo.climate, activeLayer);

  // Advice subtitle priority: worst-risk advice → active-layer advice → fallback.
  const adviceText =
    worstRisk?.advice ?? activeStat?.advice ?? DEFAULT_ADVICE_FALLBACK;

  const timestampSource =
    worstRisk?.lastUpdated ?? activeStat?.lastUpdated ?? null;
  const [timeAgoLabel, setTimeAgoLabel] = useState(() =>
    timestampSource ? formatTimeAgo(timestampSource) : 'Unknown',
  );

  useEffect(() => {
    if (!timestampSource || !regionInfo.visible) {
      setTimeAgoLabel(timestampSource ? formatTimeAgo(timestampSource) : 'Unknown');
      return;
    }
    setTimeAgoLabel(formatTimeAgo(timestampSource));
    const interval = setInterval(() => {
      setTimeAgoLabel(formatTimeAgo(timestampSource));
    }, 60_000);
    return () => clearInterval(interval);
  }, [timestampSource, regionInfo.visible]);

  const animateHeart = useCallback(() => {
    Animated.spring(heartScale, {
      toValue: 0.7,
      useNativeDriver: true,
      speed: 20,
      bounciness: 10,
    }).start(() => {
      Animated.spring(heartScale, {
        toValue: 1,
        useNativeDriver: true,
        speed: 20,
        bounciness: 10,
      }).start();
    });
  }, [heartScale]);

  const prevRegionIdRef = useRef(regionInfo.regionId);

  useEffect(() => {
    if (regionInfo.visible) {
      bottomSheetRef.current?.present();
    } else {
      bottomSheetRef.current?.dismiss();
      setIsSnackbarVisible(false);
      setDeletedFavorite(null);
    }
  }, [regionInfo.visible]);

  useEffect(() => {
    if (prevRegionIdRef.current !== regionInfo.regionId) {
      setIsSnackbarVisible(false);
      setDeletedFavorite(null);
      prevRegionIdRef.current = regionInfo.regionId;
    }
  }, [regionInfo.regionId]);

  const handleSheetChanges = useCallback(
    (index: number) => {
      if (index === -1 && regionInfo.visible) closeRegionInfo();
    },
    [regionInfo.visible, closeRegionInfo],
  );

  const handleSheetDismiss = useCallback(() => {
    if (!useMapStore.getState().regionInfo.visible) clearRegionInfo();
  }, [clearRegionInfo]);

  const handleFavoriteToggle = useCallback(() => {
    if (!regionInfo.regionId || !regionInfo.regionName) return;
    animateHeart();
    if (isFavorite(regionInfo.regionId)) {
      const favoriteToRemove =
        getFavorite(regionInfo.regionId) ?? {
          regionId: regionInfo.regionId,
          regionName: regionInfo.regionName,
          regionType: (regionInfo.regionType || 'ssc') as FavoriteLocation['regionType'],
          latitude: regionInfo.latitude ?? undefined,
          longitude: regionInfo.longitude ?? undefined,
          timestamp: new Date().toISOString(),
        };
      setDeletedFavorite(favoriteToRemove);
      removeFavorite(regionInfo.regionId);
      setIsSnackbarVisible(true);
    } else {
      setIsSnackbarVisible(false);
      setDeletedFavorite(null);
      addFavorite({
        regionId: regionInfo.regionId,
        regionName: regionInfo.regionName,
        regionType: (regionInfo.regionType || 'ssc') as FavoriteLocation['regionType'],
        latitude: regionInfo.latitude ?? undefined,
        longitude: regionInfo.longitude ?? undefined,
        timestamp: new Date().toISOString(),
      });
    }
  }, [
    addFavorite,
    animateHeart,
    getFavorite,
    isFavorite,
    regionInfo.latitude,
    regionInfo.longitude,
    regionInfo.regionId,
    regionInfo.regionName,
    regionInfo.regionType,
    removeFavorite,
  ]);

  const handleUndoFavorite = useCallback(() => {
    if (!deletedFavorite) return;
    restoreFavorite(deletedFavorite);
    setDeletedFavorite(null);
    setIsSnackbarVisible(false);
  }, [deletedFavorite, restoreFavorite]);

  const handleDismissSnackbar = useCallback(() => {
    setIsSnackbarVisible(false);
    setDeletedFavorite(null);
  }, []);

  const isFav = regionInfo.regionId ? isFavorite(regionInfo.regionId) : false;

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
    [],
  );

  return (
    <BottomSheetModal
      ref={bottomSheetRef}
      index={0}
      snapPoints={snapPoints}
      onChange={handleSheetChanges}
      onDismiss={handleSheetDismiss}
      enablePanDownToClose={true}
      backdropComponent={renderBackdrop}
      backgroundStyle={styles.sheetBackground}
      handleIndicatorStyle={styles.dragHandle}
    >
      <BottomSheetScrollView contentContainerStyle={styles.scrollContent}>
        {/* Region header */}
        <View style={styles.headerRow}>
          <View style={styles.headerTextColumn}>
            <Text style={styles.regionName} numberOfLines={2}>
              {regionInfo.regionName || 'Selected Region'}
            </Text>
            <Text
              style={styles.adviceSubtitle}
              testID="health-advice-subtitle"
              numberOfLines={3}
            >
              {adviceText}
            </Text>
          </View>
          <Pressable
            onPress={handleFavoriteToggle}
            style={styles.favoriteButton}
            hitSlop={10}
          >
            <Animated.View style={{ transform: [{ scale: heartScale }] }}>
              <Icon
                name={isFav ? 'cards-heart' : 'cards-heart-outline'}
                size={24}
                color={isFav ? '#ba1a1a' : HEALTH_SHEET_COLORS.onSurfaceVariant}
              />
            </Animated.View>
          </Pressable>
        </View>

        {/* Current Conditions section */}
        <View style={styles.currentConditionsSection}>
          <View style={styles.currentConditionsHeader}>
            <Text style={styles.sectionLabel}>CURRENT CONDITIONS</Text>
            <BaselinePill
              regionSscId={regionInfo.regionId}
              climate={regionInfo.climate}
            />
          </View>
          <ClimateMetricsGrid climate={regionInfo.climate} />
        </View>

        {/* Health Impact Data */}
        <View style={styles.impactSection}>
          <View style={styles.impactSectionHeader}>
            <Icon name="chart-timeline-variant" size={20} color={HEALTH_SHEET_COLORS.outline} />
            <Text style={styles.impactSectionTitle}>HEALTH IMPACT DATA</Text>
          </View>
          <View style={styles.impactCard}>
            <View style={styles.impactCardTop}>
              <Text style={styles.impactCardTitle}>Respiratory Hospitalizations</Text>
              <Text style={[styles.impactStatus, { color: IMPACT_COLORS.elevated }]}>ELEVATED</Text>
            </View>
            <Text style={styles.impactCardText}>
              PM2.5 levels of 35 µg/m³ correlate with{' '}
              <Text style={styles.textBold}>15% higher</Text> respiratory admission rates.
            </Text>
          </View>
          <View style={styles.impactCard}>
            <View style={styles.impactCardTop}>
              <Text style={styles.impactCardTitle}>Cardiovascular Hospitalizations</Text>
              <Text style={[styles.impactStatus, { color: HEALTH_SHEET_COLORS.outline }]}>MODERATE</Text>
            </View>
            <Text style={styles.impactCardText}>
              Current levels associated with marginally elevated cardiovascular risk factors.
            </Text>
          </View>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>Data source: Open-Meteo API | Aggregated health data</Text>
          <Text style={[styles.footerText, styles.footerTextBold]}>
            Last updated: {timeAgoLabel}
          </Text>
        </View>
      </BottomSheetScrollView>
      <Snackbar
        visible={isSnackbarVisible}
        onDismiss={handleDismissSnackbar}
        duration={3000}
        wrapperStyle={styles.snackbarWrapper}
        action={{ label: 'Undo', onPress: handleUndoFavorite }}
      >
        Deleted
      </Snackbar>
    </BottomSheetModal>
  );
};

const styles = StyleSheet.create({
  sheetBackground: {
    backgroundColor: HEALTH_SHEET_COLORS.surface,
    borderRadius: 24,
    ...Platform.select({
      ios: {
        shadowColor: '#001C3A',
        shadowOffset: { width: 0, height: -8 },
        shadowOpacity: 0.06,
        shadowRadius: 32,
      },
      android: { elevation: 16 },
    }),
  },
  dragHandle: {
    width: 32,
    height: 4,
    backgroundColor: HEALTH_SHEET_COLORS.outlineVariant,
    borderRadius: 2,
    marginTop: 8,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingBottom: 40,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    paddingTop: 16,
    marginBottom: 24,
    gap: 12,
  },
  headerTextColumn: {
    flex: 1,
    minWidth: 0,
  },
  regionName: {
    fontSize: 24,
    fontWeight: '700',
    color: HEALTH_SHEET_COLORS.onSurface,
    letterSpacing: -0.5,
    marginBottom: 4,
  },
  adviceSubtitle: {
    fontSize: 13,
    fontWeight: '500',
    lineHeight: 18,
    color: HEALTH_SHEET_COLORS.onSurfaceVariant,
    opacity: 0.8,
  },
  favoriteButton: {
    padding: 8,
    marginTop: -8,
  },
  currentConditionsSection: {
    marginBottom: 32,
  },
  currentConditionsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    color: HEALTH_SHEET_COLORS.outline,
    letterSpacing: 1,
  },
  impactSection: {
    paddingTop: 16,
    gap: 16,
  },
  impactSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  impactSectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    color: HEALTH_SHEET_COLORS.outline,
  },
  impactCard: {
    backgroundColor: 'rgba(242, 243, 252, 0.5)',
    borderRadius: 16,
    padding: 24,
    gap: 12,
  },
  impactCardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 8,
  },
  impactCardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: HEALTH_SHEET_COLORS.onSurface,
    lineHeight: 20,
    flexShrink: 1,
  },
  impactStatus: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  impactCardText: {
    fontSize: 14,
    lineHeight: 22,
    color: HEALTH_SHEET_COLORS.onSurfaceVariant,
  },
  textBold: {
    fontWeight: '700',
    color: HEALTH_SHEET_COLORS.onSurface,
  },
  footer: {
    marginTop: 32,
    paddingTop: 16,
    gap: 4,
  },
  footerText: {
    fontSize: 11,
    color: HEALTH_SHEET_COLORS.outline,
    lineHeight: 14,
  },
  footerTextBold: {
    fontWeight: '500',
  },
  snackbarWrapper: {
    bottom: 100,
  },
});

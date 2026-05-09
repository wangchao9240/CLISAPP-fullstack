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
import { ClimateMetricsGrid } from '../UI/ClimateMetricsGrid';
import { TodayVsReferenceBand } from '../UI/TodayVsReferenceBand';
import { getClimateDeltaState } from '../../utils/climateDelta';
import {
  HEALTH_SHEET_COLORS,
  RISK_TEXT_COLORS,
} from '../../constants/healthDesignTokens';
import { PALETTE, RADII, TABULAR_NUMS, TYPE_SCALE } from '../../constants/designTokens';
import { useMapStore } from '../../store/mapStore';
import { FavoriteLocation, useFavoritesStore } from '../../store/favoritesStore';
import type { RiskKey } from '../../constants/healthDesignTokens';

const SNAP_POINTS = ['30%', '60%', '85%'];
const DEFAULT_ADVICE_FALLBACK = 'Conditions are within expected ranges.';

// Heart button color per spec — not a palette token, a documented exception.
const HEART_ACTIVE_COLOR = '#C24B22';

const LAYER_SHORT_LABELS: Record<string, string> = {
  pm25: 'PM2.5',
  uv: 'UV',
  temperature: 'Temp',
  humidity: 'Humidity',
  precipitation: 'Precip',
};

export const HealthBottomSheet: React.FC = () => {
  const bottomSheetRef = useRef<BottomSheetModal>(null);
  const heartScale = useRef(new Animated.Value(1)).current;
  const [deletedFavorite, setDeletedFavorite] = useState<FavoriteLocation | null>(null);
  const [isSnackbarVisible, setIsSnackbarVisible] = useState(false);
  const [currentSnapIndex, setCurrentSnapIndex] = useState(0);

  const { regionInfo, activeLayer, closeRegionInfo, clearRegionInfo } = useMapStore();

  const { isFavorite, addFavorite, restoreFavorite, removeFavorite, getFavorite } =
    useFavoritesStore();

  const snapPoints = useMemo(() => SNAP_POINTS, []);

  const worstRisk = getWorstRiskStat(regionInfo.climate);
  const activeStat = getActiveClimateStat(regionInfo.climate, activeLayer);
  const tempStat = getActiveClimateStat(regionInfo.climate, 'temperature');

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
      setCurrentSnapIndex(index);
      useMapStore.getState().setBottomSheetSnapIndex(index);
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

  const handlePullUp = useCallback(() => {
    bottomSheetRef.current?.snapToIndex(1);
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

  // Build tag line for peek header
  const tagLine = useMemo(() => {
    const name = regionInfo.regionName ?? '';
    const sscId = regionInfo.regionId ?? '';
    const regionType = regionInfo.regionType ?? '';
    if (sscId && regionType) {
      return `QLD · ${name} · ${regionType.toUpperCase()} ${sscId}`;
    }
    return `QLD · ${name}`;
  }, [regionInfo.regionName, regionInfo.regionId, regionInfo.regionType]);

  // Delta state for "vs 1890-1960" stat
  const deltaState = useMemo(
    () => getClimateDeltaState(regionInfo.regionId, regionInfo.climate),
    [regionInfo.regionId, regionInfo.climate],
  );

  // Risk color for peek stat strip
  const riskCategory = worstRisk?.category ?? worstRisk?.riskLevel ?? null;
  const riskColor =
    riskCategory && riskCategory in RISK_TEXT_COLORS
      ? RISK_TEXT_COLORS[riskCategory as RiskKey]
      : PALETTE.fg;

  // Driver label — names the layer responsible for the worst-risk advice/badge.
  // Only shown when worstRisk drives the displayed advice (otherwise the active
  // layer is already the focus of the user's attention).
  const driverLabel =
    worstRisk?.layer
      ? LAYER_SHORT_LABELS[worstRisk.layer] ?? worstRisk.name ?? null
      : null;

  // Delta color for peek stat strip — cool if below, warm if above
  const deltaColor =
    deltaState.variant === 'cool'
      ? PALETTE.cool
      : deltaState.variant === 'warm'
      ? PALETTE.warm
      : PALETTE.fg;

  // Shared heart button — used in both peek and full content
  const HeartButton = (
    <Pressable
      testID="favorite-button"
      onPress={handleFavoriteToggle}
      style={styles.peekHeartButton}
      hitSlop={10}
    >
      <Animated.View style={{ transform: [{ scale: heartScale }] }}>
        <Icon
          name={isFav ? 'cards-heart' : 'cards-heart-outline'}
          size={22}
          color={isFav ? HEART_ACTIVE_COLOR : PALETTE.muted}
        />
      </Animated.View>
    </Pressable>
  );

  // Formatted timestamp for sources footer
  const formattedTimestamp = useMemo(() => {
    if (!timestampSource) return 'Unknown';
    try {
      return new Intl.DateTimeFormat('en-AU', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      }).format(new Date(timestampSource));
    } catch {
      return timeAgoLabel;
    }
  }, [timestampSource, timeAgoLabel]);

  // Tag line variants for full content
  const fullTagLineCollapsed = useMemo(() => {
    const parts: string[] = ['QLD'];
    if (regionInfo.regionName) parts.push(regionInfo.regionName);
    parts.push(`Updated ${timeAgoLabel}`);
    return parts.join(' · ');
  }, [regionInfo.regionName, timeAgoLabel]);

  const fullTagLineExpanded = useMemo(() => {
    const parts: string[] = ['QLD'];
    if (regionInfo.regionName) parts.push(regionInfo.regionName);
    if (regionInfo.regionId) parts.push(`SSC ${regionInfo.regionId}`);
    return parts.join(' · ');
  }, [regionInfo.regionName, regionInfo.regionId]);

  const isExpanded = currentSnapIndex === 2;

  // ── Peek content (snap index 0) ─────────────────────────────────────────────
  const PeekContent = (
    <View style={styles.peekContainer}>
      {/* Header row: name + heart */}
      <View style={styles.peekHeaderRow}>
        <View style={styles.peekHeaderText}>
          <Text style={styles.peekName} numberOfLines={1}>
            {regionInfo.regionName || 'Selected Region'}
          </Text>
          <Text style={styles.peekTag} numberOfLines={1}>
            {tagLine}
          </Text>
        </View>
        {HeartButton}
      </View>

      {/* Advice subtitle */}
      <Text
        style={styles.peekAdvice}
        testID="health-advice-subtitle"
        numberOfLines={2}
      >
        {adviceText}
      </Text>

      {/* Driver tag — clarifies which layer drove the advice */}
      {driverLabel && (
        <Text style={styles.driverTag} testID="health-advice-driver">
          {`Driver · ${driverLabel}`}
        </Text>
      )}

      {/* Divider */}
      <View style={styles.peekDivider} />

      {/* 3-stat strip */}
      <View style={styles.peekStatRow}>
        {/* Risk */}
        <View style={styles.peekStat}>
          <Text style={styles.peekStatLabel}>
            {driverLabel ? `Risk · ${driverLabel}` : 'Risk'}
          </Text>
          <Text style={[styles.peekStatValue, { color: riskColor }]} {...TABULAR_NUMS}>
            {worstRisk?.category ?? worstRisk?.riskLevel ?? '—'}
          </Text>
        </View>

        <View style={styles.peekStatDivider} />

        {/* Temp */}
        <View style={styles.peekStat}>
          <Text style={styles.peekStatLabel}>Temp</Text>
          <Text style={styles.peekStatValue} {...TABULAR_NUMS}>
            {tempStat?.value !== undefined ? (
              <>
                {String(tempStat.value)}
                <Text style={styles.peekStatUnit}> °C</Text>
              </>
            ) : (
              '—'
            )}
          </Text>
        </View>

        {/* vs 1890-1960 — only shown when delta is available */}
        {deltaState.variant !== 'unavailable' && deltaState.deltaLabel !== null && (
          <>
            <View style={styles.peekStatDivider} />
            <View style={styles.peekStat}>
              <Text style={styles.peekStatLabel}>vs 1890–1960</Text>
              <Text style={[styles.peekStatValue, { color: deltaColor }]} {...TABULAR_NUMS}>
                {deltaState.deltaLabel}
                <Text style={styles.peekStatUnit}> °C</Text>
              </Text>
            </View>
          </>
        )}
      </View>

      {/* Pull-up CTA */}
      <Pressable onPress={handlePullUp} style={styles.peekCta} hitSlop={8}>
        <Icon name="chevron-up" size={14} color={PALETTE.muted} />
        <Text style={styles.peekCtaText}>Pull up for full details</Text>
      </Pressable>
    </View>
  );

  // ── Full content (snap index >= 1) ──────────────────────────────────────────
  const FullContent = (
    <>
      {/* Region header */}
      <View style={styles.fullHeaderRow}>
        <View style={styles.fullHeaderText}>
          <Text
            style={isExpanded ? styles.fullRegionNameExpanded : styles.fullRegionNameCollapsed}
            numberOfLines={2}
          >
            {regionInfo.regionName || 'Selected Region'}
          </Text>
          <Text style={styles.fullTagLine} numberOfLines={1}>
            {isExpanded ? fullTagLineExpanded : fullTagLineCollapsed}
          </Text>
        </View>
        {/* Heart button — 40×40 circle, #C24B22 active, PALETTE.muted inactive */}
        <Pressable
          testID="favorite-button"
          onPress={handleFavoriteToggle}
          style={styles.fullHeartButton}
          hitSlop={10}
        >
          <Animated.View style={{ transform: [{ scale: heartScale }] }}>
            <Icon
              name={isFav ? 'cards-heart' : 'cards-heart-outline'}
              size={22}
              color={isFav ? HEART_ACTIVE_COLOR : PALETTE.muted}
            />
          </Animated.View>
        </Pressable>
      </View>

      {/* Advice subtitle */}
      <Text
        style={isExpanded ? styles.adviceSubtitleExpanded : styles.adviceSubtitleCollapsed}
        testID="health-advice-subtitle"
        numberOfLines={3}
      >
        {adviceText}
      </Text>

      {/* Driver tag — clarifies which layer drove the advice */}
      {driverLabel && (
        <Text style={styles.driverTag} testID="health-advice-driver-full">
          {`Driver · ${driverLabel}`}
        </Text>
      )}

      {/* TODAY VS REFERENCE band */}
      {isExpanded && (
        <Text style={[styles.currentConditionsLabel, { marginTop: 26, marginBottom: 10 }]}>
          TODAY VS REFERENCE
        </Text>
      )}
      <TodayVsReferenceBand
        regionSscId={regionInfo.regionId}
        climate={regionInfo.climate}
        variant={isExpanded ? 'expanded' : 'collapsed'}
      />

      {/* Current Conditions label */}
      <Text style={styles.currentConditionsLabel}>CURRENT CONDITIONS</Text>

      {/* Metrics grid */}
      <ClimateMetricsGrid climate={regionInfo.climate} />

      {/* EXPANDED ONLY: How to read this */}
      {isExpanded && (
        <View style={styles.explainerCard}>
          <View style={styles.explainerHeader}>
            <Icon name="information-outline" size={14} color={PALETTE.accentDeep} />
            <Text style={styles.explainerHeaderText}>HOW TO READ THIS</Text>
          </View>
          <Text style={styles.explainerBody}>
            <Text style={styles.explainerBold}>Climate</Text>
            {' is the long-term shift versus pre-industrial Australia. '}
            <Text style={styles.explainerBold}>Rainfall</Text>
            {' tracks precipitation against the seasonal norm, month-to-date.'}
          </Text>
        </View>
      )}

      {/* EXPANDED ONLY: Sources footer */}
      {isExpanded && (
        <View style={styles.sourcesFooter}>
          <View style={styles.sourceRow}>
            <Text style={styles.sourceKey}>UPDATED</Text>
            <Text style={styles.sourceValue} {...TABULAR_NUMS}>
              {formattedTimestamp}
            </Text>
          </View>
          <View style={styles.sourceRow}>
            <Text style={styles.sourceKey}>SOURCES</Text>
            <Text style={[styles.sourceValue, styles.sourceMono]}>
              BoM · ERA5 reanalysis · ABS SSC 2021
            </Text>
          </View>
          <View style={styles.sourceRow}>
            <Text style={styles.sourceKey}>BASELINE</Text>
            <Text style={[styles.sourceValue, styles.sourceMono]}>
              CRU TS / 1890–1960 (Cortes-Ramirez et al.)
            </Text>
          </View>
        </View>
      )}
    </>
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
        {currentSnapIndex === 0 ? PeekContent : FullContent}
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
        shadowColor: '#0D1220',
        shadowOffset: { width: 0, height: -4 },
        shadowOpacity: 0.12,
        shadowRadius: 24,
      },
      android: { elevation: 16 },
    }),
  },
  dragHandle: {
    width: 36,
    height: 4,
    backgroundColor: PALETTE.border2,
    borderRadius: 3,
    marginTop: 8,
  },
  scrollContent: {
    paddingHorizontal: 22,
    paddingBottom: 28,
  },

  // ── Peek styles ─────────────────────────────────────────────────────────────
  peekContainer: {
    paddingTop: 14,
  },
  peekHeaderRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 14,
    marginBottom: 6,
  },
  peekHeaderText: {
    flex: 1,
    minWidth: 0,
  },
  peekName: {
    fontSize: 26,
    fontWeight: '700',
    letterSpacing: -0.52,
    lineHeight: 28,
    color: PALETTE.fg,
  },
  peekTag: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.66,
    textTransform: 'uppercase',
    color: PALETTE.muted,
    marginTop: 6,
  },
  peekHeartButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: PALETTE.border,
    backgroundColor: PALETTE.surface,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  peekAdvice: {
    fontSize: 14,
    lineHeight: 20,
    color: PALETTE.muted,
    marginTop: 8,
  },
  driverTag: {
    fontSize: 10.5,
    fontWeight: '600',
    letterSpacing: 0.66,
    textTransform: 'uppercase',
    color: PALETTE.fg2,
    marginTop: 6,
  },
  peekDivider: {
    height: 1,
    backgroundColor: PALETTE.border,
    marginTop: 14,
    marginBottom: 12,
  },
  peekStatRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  peekStat: {
    flexDirection: 'column',
    gap: 2,
  },
  peekStatLabel: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: PALETTE.muted,
  },
  peekStatValue: {
    fontSize: 18,
    fontWeight: '600',
    letterSpacing: -0.18,
    color: PALETTE.fg,
  },
  peekStatUnit: {
    fontSize: 12,
    fontWeight: '500',
    color: PALETTE.muted,
  },
  peekStatDivider: {
    width: 1,
    alignSelf: 'stretch',
    backgroundColor: PALETTE.border,
  },
  peekCta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginTop: 14,
  },
  peekCtaText: {
    fontSize: 12,
    fontWeight: '500',
    color: PALETTE.muted,
  },

  // ── Full content styles ──────────────────────────────────────────────────────
  fullHeaderRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    paddingTop: 16,
    gap: 12,
  },
  fullHeaderText: {
    flex: 1,
    minWidth: 0,
  },
  fullRegionNameCollapsed: {
    fontSize: 28,
    fontWeight: '700',
    letterSpacing: -0.56,
    lineHeight: 30,
    color: PALETTE.fg,
  },
  fullRegionNameExpanded: {
    ...TYPE_SCALE.title,
    color: PALETTE.fg,
  },
  fullTagLine: {
    fontSize: 10.5,
    fontWeight: '600',
    letterSpacing: 0.63,
    textTransform: 'uppercase',
    color: PALETTE.muted,
    marginTop: 6,
  },
  fullHeartButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: PALETTE.border,
    backgroundColor: PALETTE.surface,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  adviceSubtitleCollapsed: {
    fontSize: 14,
    lineHeight: 21,
    color: PALETTE.muted,
    marginTop: 8,
  },
  adviceSubtitleExpanded: {
    fontSize: 15,
    lineHeight: 22,
    color: PALETTE.fg2,
    marginTop: 14,
  },
  currentConditionsLabel: {
    ...TYPE_SCALE.kicker,
    color: PALETTE.muted,
    marginTop: 18,
    marginBottom: 12,
  },

  // ── Expanded-only: explainer card ───────────────────────────────────────────
  explainerCard: {
    backgroundColor: PALETTE.accentSoft,
    borderWidth: 1,
    borderColor: 'rgba(11,134,200,0.18)',
    borderRadius: RADII.control,
    padding: 14,
    paddingHorizontal: 16,
    marginTop: 22,
  },
  explainerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  explainerHeaderText: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.66,
    textTransform: 'uppercase',
    color: PALETTE.accentDeep,
  },
  explainerBody: {
    fontSize: 13,
    lineHeight: 19,
    color: PALETTE.fg2,
    marginTop: 8,
  },
  explainerBold: {
    fontWeight: '600',
    color: PALETTE.fg,
  },

  // ── Expanded-only: sources footer ───────────────────────────────────────────
  sourcesFooter: {
    marginTop: 22,
    paddingTop: 18,
    borderTopWidth: 1,
    borderTopColor: PALETTE.border,
    gap: 10,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  sourceKey: {
    fontSize: 10.5,
    fontWeight: '600',
    letterSpacing: 0.84,
    textTransform: 'uppercase',
    color: PALETTE.fg2,
    minWidth: 80,
  },
  sourceValue: {
    fontSize: 11.5,
    color: PALETTE.muted,
    flex: 1,
  },
  sourceMono: {
    // System mono fallback — fontFamily not reliably available cross-platform
    letterSpacing: 0.2,
  },

  snackbarWrapper: {
    bottom: 100,
  },
});

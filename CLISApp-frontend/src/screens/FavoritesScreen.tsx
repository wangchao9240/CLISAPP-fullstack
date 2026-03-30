import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FlatList, StyleSheet, Text, View } from 'react-native';
import { Snackbar } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import { FavoriteLocationCard } from '../components/UI/FavoriteLocationCard';
import {
  useFavoritesStore,
  FavoriteLocation,
} from '../store/favoritesStore';
import { useMapStore } from '../store/mapStore';
import { apiService } from '../services/ApiService';
import { formatClimateOverview } from '../hooks/useApi';
import { loadRegionBoundary } from '../services/boundaries/boundaryLoader';
import type { RegionClimateOverview } from '../types/region.types';

interface FavoritesScreenProps {
  onNavigateToMap?: () => void;
}

export const FavoritesScreen: React.FC<FavoritesScreenProps> = ({
  onNavigateToMap,
}) => {
  const favorites = useFavoritesStore((s) => s.favorites);
  const removeFavorite = useFavoritesStore((s) => s.removeFavorite);
  const restoreFavorite = useFavoritesStore((s) => s.restoreFavorite);

  const [deletedFavorite, setDeletedFavorite] =
    useState<FavoriteLocation | null>(null);
  const [isSnackbarVisible, setIsSnackbarVisible] = useState(false);
  const [climateMap, setClimateMap] = useState<
    Record<string, RegionClimateOverview>
  >({});
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set());
  const climateMapRef = useRef(climateMap);
  const loadingIdsRef = useRef(loadingIds);

  useEffect(() => {
    climateMapRef.current = climateMap;
  }, [climateMap]);

  useEffect(() => {
    loadingIdsRef.current = loadingIds;
  }, [loadingIds]);

  useEffect(() => {
    const toFetch = favorites.filter(
      (favorite) =>
        !climateMapRef.current[favorite.regionId] &&
        !loadingIdsRef.current.has(favorite.regionId),
    );

    if (toFetch.length === 0) {
      return;
    }

    setLoadingIds((prev) => {
      const next = new Set(prev);
      toFetch.forEach((favorite) => next.add(favorite.regionId));
      return next;
    });

    toFetch.forEach(async (favorite) => {
      try {
        const response = await apiService.getRegionInfo(favorite.regionId, true);
        if (response.success && response.data?.current_climate) {
          const overview = formatClimateOverview(
            response.data.current_climate,
            'temperature',
          );
          setClimateMap((prev) => ({
            ...prev,
            [favorite.regionId]: overview,
          }));
        }
      } catch {
        // Climate fetch failure is non-critical; the card shows "No data".
      } finally {
        setLoadingIds((prev) => {
          const next = new Set(prev);
          next.delete(favorite.regionId);
          return next;
        });
      }
    });
  }, [favorites]);

  const handleDelete = useCallback(
    (favorite: FavoriteLocation) => {
      setDeletedFavorite(favorite);
      removeFavorite(favorite.regionId);
      setIsSnackbarVisible(true);
    },
    [removeFavorite],
  );

  const handleUndo = useCallback(() => {
    if (deletedFavorite) {
      restoreFavorite(deletedFavorite);
    }
    setIsSnackbarVisible(false);
    setDeletedFavorite(null);
  }, [deletedFavorite, restoreFavorite]);

  const handleSnackbarDismiss = useCallback(() => {
    setIsSnackbarVisible(false);
    setDeletedFavorite(null);
  }, []);

  const handleCardPress = useCallback(
    async (favorite: FavoriteLocation) => {
      if (favorite.latitude == null || favorite.longitude == null) {
        return;
      }

      const {
        setRegion,
        setSelectedRegion,
        setRegionInfoLoading,
        setRegionInfoError,
        openRegionInfo,
        setRegionBoundary,
        activeLayer,
      } = useMapStore.getState();

      const deltas = { latitudeDelta: 0.05, longitudeDelta: 0.05 };
      setRegion({
        latitude: favorite.latitude,
        longitude: favorite.longitude,
        ...deltas,
      });
      setSelectedRegion(favorite.regionId);
      setRegionInfoLoading(true);

      try {
        const response = await apiService.getRegionInfo(
          favorite.regionId,
          true,
        );
        if (response.success && response.data) {
          const overview = formatClimateOverview(
            response.data.current_climate,
            activeLayer,
          );
          openRegionInfo({
            regionId: response.data.id,
            regionName: response.data.name,
            regionType: response.data.type,
            latitude: response.data.location.latitude,
            longitude: response.data.location.longitude,
            climate: overview,
          });
        } else {
          setRegionInfoError('No climate data available for this region');
        }
      } catch {
        setRegionInfoError('Failed to load region information');
      }

      loadRegionBoundary(favorite.regionId)
        .then((boundary) => {
          setRegionBoundary(boundary);
        })
        .catch(() => {
          // Boundary load failure is non-critical
        });

      onNavigateToMap?.();
    },
    [onNavigateToMap],
  );

  const renderItem = useCallback(
    ({ item }: { item: FavoriteLocation }) => (
      <FavoriteLocationCard
        favorite={item}
        climate={climateMap[item.regionId] ?? null}
        isClimateLoading={loadingIds.has(item.regionId)}
        onPress={() => handleCardPress(item)}
        onDelete={() => handleDelete(item)}
      />
    ),
    [climateMap, handleCardPress, handleDelete, loadingIds],
  );

  const keyExtractor = useCallback(
    (item: FavoriteLocation) => item.regionId,
    [],
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Favorites</Text>
      </View>

      {favorites.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIllustration}>
            <View style={styles.emptyIconContainer}>
              <MaterialIcons name="location-on" size={80} color="#005dac" />
              <View style={styles.emptyHeartOverlay}>
                <Icon name="heart" size={24} color="#944700" />
              </View>
            </View>
          </View>
          <Text style={styles.emptyTitle}>No Favorites Yet</Text>
          <Text style={styles.emptyHint}>
            Tap the heart icon on the map to save your important places.
          </Text>
          {onNavigateToMap && (
            <View style={styles.openMapButton}>
              <Text
                style={styles.openMapButtonText}
                onPress={onNavigateToMap}
                accessibilityRole="button"
              >
                Open Map
              </Text>
            </View>
          )}
        </View>
      ) : (
        <FlatList
          data={favorites}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
        />
      )}

      <Snackbar
        visible={isSnackbarVisible}
        onDismiss={handleSnackbarDismiss}
        duration={3000}
        action={{ label: 'Undo', onPress: handleUndo }}
        style={styles.snackbar}
      >
        Deleted
      </Snackbar>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9F9FF',
  },
  header: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    height: 56,
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#181C21',
    letterSpacing: -0.3,
  },
  listContent: {
    paddingVertical: 8,
    paddingBottom: 100,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  emptyIllustration: {
    width: 120,
    height: 120,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  emptyIconContainer: {
    width: 120,
    height: 120,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F2F3FC',
    borderRadius: 16,
    position: 'relative',
  },
  emptyHeartOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 6,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#181C21',
    marginBottom: 8,
    letterSpacing: -0.3,
  },
  emptyHint: {
    fontSize: 14,
    color: '#414752',
    textAlign: 'center',
    lineHeight: 20,
    maxWidth: 280,
  },
  openMapButton: {
    marginTop: 32,
    backgroundColor: '#005dac',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 16,
  },
  openMapButtonText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#FFFFFF',
  },
  snackbar: {
    marginBottom: 8,
  },
});

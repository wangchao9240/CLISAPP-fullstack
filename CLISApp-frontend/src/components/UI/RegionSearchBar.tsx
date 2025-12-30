import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  View,
  TextInput,
  FlatList,
  TouchableOpacity,
  Text,
  StyleSheet,
  Keyboard,
} from 'react-native';
import { useRegionSearch, formatClimateOverview } from '../../hooks/useApi';
import { RegionSearchResult } from '../../services/ApiService';
import { useMapStore } from '../../store/mapStore';
import { Region } from '../../types/map.types';
import { apiService } from '../../services/ApiService';

interface RegionSearchBarProps {
  style?: any;
}

export const RegionSearchBar: React.FC<RegionSearchBarProps> = ({ style }) => {
  const [query, setQuery] = useState('');
  const [suppressSearch, setSuppressSearch] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const { data, loading, error, searchRegions, clearResults } = useRegionSearch();
  const { setRegion, setMapLevel, setSelectedRegion, setLoading, openRegionInfo, setRegionInfoLoading, setRegionInfoError, closeRegionInfo, setRegionBoundary } = useMapStore();

  useEffect(() => {
    if (suppressSearch) {
      return;
    }

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (query.trim().length < 2) {
      clearResults();
      return;
    }

    debounceRef.current = setTimeout(() => {
      searchRegions(query.trim(), undefined, 5);
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, suppressSearch, searchRegions, clearResults]);

  const handleSelect = useCallback((item: RegionSearchResult) => {
    setSuppressSearch(true);
    setQuery(item.name);
    clearResults();
    Keyboard.dismiss();

    const deltas = getDeltasForType(item.type);
    const targetRegion: Region = {
      latitude: item.location.latitude,
      longitude: item.location.longitude,
      latitudeDelta: deltas.latitudeDelta,
      longitudeDelta: deltas.longitudeDelta,
    };

    setRegion(targetRegion);
    setSelectedRegion(item.id);
    setLoading(true);

    const targetLevel = inferMapLevel(item.type);
    if (targetLevel) {
      setMapLevel(targetLevel);
    }

    setRegionInfoLoading(true);
    
    // Fetch region info by ID (保持用户选择的区域类型，不会因为坐标查询而改变)
    apiService.getRegionInfo(item.id, true)
      .then((response) => {
        if (!response.success || !response.data) {
          setRegionInfoError('No climate data available for this region');
          return;
        }
        const info = response.data;
        const overview = formatClimateOverview(info.current_climate, useMapStore.getState().activeLayer);
        openRegionInfo({
          regionId: info.id,
          regionName: info.name,
          regionType: info.type,
          climate: overview,
        });
      })
      .catch((err) => {
        console.error('Failed to load region info', err);
        setRegionInfoError('Failed to load region information');
      });

    // Fetch region boundary
    apiService.getRegionBoundary(item.id)
      .then((response) => {
        if (response.success && response.data) {
          const feature = response.data;
          // Convert GeoJSON coordinates to React Native Maps format
          const coordinates = convertGeoJSONToMapCoordinates(feature.geometry);
          setRegionBoundary({
            regionId: item.id,
            coordinates,
            properties: feature.properties,
          });
        } else {
          console.warn('Failed to fetch region boundary:', response.error);
          setRegionBoundary(null);
        }
      })
      .catch((err) => {
        console.error('Failed to load region boundary', err);
        setRegionBoundary(null);
      });
  }, [setRegion, setMapLevel, clearResults, setSelectedRegion, setLoading, openRegionInfo, setRegionInfoLoading, setRegionInfoError, setRegionBoundary]);


  const handleChangeText = useCallback((text: string) => {
    setSuppressSearch(false);
    setQuery(text);
    if (text.trim().length === 0) {
      closeRegionInfo();
      setRegionBoundary(null);
    }
  }, [closeRegionInfo, setRegionBoundary]);

  return (
    <View style={[styles.container, style]}>
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          value={query}
          placeholder="Search location or suburb"
          placeholderTextColor="rgba(10, 10, 10, 0.5)"
          onChangeText={handleChangeText}
          accessibilityLabel="Region search"
          returnKeyType="search"
        />
        {loading && <ActivityIndicator style={styles.indicator} size="small" color="#0A0A0A" />}
      </View>
      {!loading && error && <Text style={styles.errorText}>{error}</Text>}
      {data.length > 0 && (
        <View style={styles.resultsContainer}>
          <FlatList
            keyboardShouldPersistTaps="handled"
            data={data}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => <ResultItem item={item} onPress={handleSelect} />}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
          />
        </View>
      )}
    </View>
  );
};

const getDeltasForType = (type: string) => {
  switch (type) {
    case 'suburb':
      return { latitudeDelta: 0.05, longitudeDelta: 0.05 };
    case 'postcode':
      return { latitudeDelta: 0.08, longitudeDelta: 0.08 };
    case 'city':
      return { latitudeDelta: 0.15, longitudeDelta: 0.15 };
    case 'lga':
    default:
      // 更大的delta值 = 更小的缩放级别 = 显示更大的区域，便于查看整个LGA边界
      return { latitudeDelta: 0.8, longitudeDelta: 0.8 };
  }
};

const inferMapLevel = (type: string) => {
  if (type === 'suburb' || type === 'postcode') {
    return 'suburb' as const;
  }
  if (type === 'lga') {
    return 'lga' as const;
  }
  return undefined;
};

const formatRegionMeta = (item: RegionSearchResult) => {
  const parts: string[] = [];
  parts.push(item.state);
  parts.push(item.type.toUpperCase());
  if (item.population) {
    parts.push(`Population ${item.population.toLocaleString()}`);
  }
  return parts.join(' · ');
};

/**
 * Convert GeoJSON geometry to React Native Maps coordinate format
 * Handles Polygon and MultiPolygon geometries
 */
const convertGeoJSONToMapCoordinates = (geometry: any): Array<Array<{ latitude: number; longitude: number }>> => {
  if (!geometry || !geometry.coordinates) {
    return [];
  }

  const convertCoordinatePair = (coord: number[]): { latitude: number; longitude: number } => ({
    latitude: coord[1],  // GeoJSON is [lng, lat]
    longitude: coord[0],
  });

  if (geometry.type === 'Polygon') {
    // Polygon: coordinates is array of rings, first ring is exterior
    return geometry.coordinates.map((ring: number[][]) => 
      ring.map(convertCoordinatePair)
    );
  } else if (geometry.type === 'MultiPolygon') {
    // MultiPolygon: coordinates is array of polygons
    return geometry.coordinates.flatMap((polygon: number[][][]) =>
      polygon.map((ring: number[][]) => ring.map(convertCoordinatePair))
    );
  }

  return [];
};

const ResultItem: React.FC<{ item: RegionSearchResult; onPress: (item: RegionSearchResult) => void }> = ({ item, onPress }) => (
  <TouchableOpacity style={styles.resultItem} onPress={() => onPress(item)}>
    <View style={styles.resultTextContainer}>
      <Text style={styles.resultName}>{item.name}</Text>
      <Text style={styles.resultMeta}>{formatRegionMeta(item)}</Text>
    </View>
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignSelf: 'flex-start',
    position: 'relative',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 16,
    paddingLeft: 12,
    paddingRight: 16,
    height: 54,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.05)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  searchIcon: {
    fontSize: 20,
    marginRight: 8,
    opacity: 0.6,
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: '#0A0A0A',
    letterSpacing: -0.31,
    padding: 0,
  },
  indicator: {
    marginLeft: 8,
  },
  errorText: {
    position: 'absolute',
    top: 58,
    left: 0,
    fontSize: 12,
    color: '#D32F2F',
  },
  resultsContainer: {
    position: 'absolute',
    top: 62,
    left: 0,
    right: 0,
    zIndex: 1000,
    borderRadius: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.98)',
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
    maxHeight: 220,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 3,
  },
  resultItem: {
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  resultTextContainer: {
    flexDirection: 'column',
  },
  resultName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
  },
  resultMeta: {
    marginTop: 2,
    fontSize: 12,
    color: '#6B7280',
  },
  separator: {
    height: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    marginHorizontal: 8,
  },
});



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
  Platform,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useRegionSearch, formatClimateOverview } from '../../hooks/useApi';
import { RegionSearchResult } from '../../services/ApiService';
import { useMapStore } from '../../store/mapStore';
import { Region } from '../../types/map.types';
import { apiService } from '../../services/ApiService';
import { loadRegionBoundary } from '../../services/boundaries/boundaryLoader';
import { PALETTE, RADII } from '../../constants/designTokens';

interface RegionSearchBarProps {
  style?: any;
}

export const RegionSearchBar: React.FC<RegionSearchBarProps> = ({ style }) => {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const [suppressSearch, setSuppressSearch] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const boundaryRequestIdRef = useRef(0);
  const inputRef = useRef<TextInput>(null);
  const { data, loading, error, searchRegions, clearResults } = useRegionSearch();
  const {
    setRegion,
    setMapLevel,
    setSelectedRegion,
    setLoading,
    openRegionInfo,
    setRegionInfoLoading,
    setRegionInfoError,
    closeRegionInfo,
    setRegionBoundary,
    pushRecentRegion,
    recentRegions,
  } = useMapStore();

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
    const currentBoundaryRequestId = ++boundaryRequestIdRef.current;
    setSuppressSearch(true);
    setQuery(item.name);
    clearResults();
    Keyboard.dismiss();
    setFocused(false);

    pushRecentRegion({ id: item.id, name: item.name });

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
          latitude: info.location.latitude,
          longitude: info.location.longitude,
          climate: overview,
        });
      })
      .catch((err) => {
        console.error('Failed to load region info', err);
        setRegionInfoError('Failed to load region information');
      });

    loadRegionBoundary(item.id)
      .then((boundary) => {
        if (boundaryRequestIdRef.current !== currentBoundaryRequestId) {
          return;
        }
        setRegionBoundary(boundary);
      })
      .catch((err) => {
        console.error('Failed to load region boundary', err);
      });
  }, [setRegion, setMapLevel, clearResults, setSelectedRegion, setLoading, openRegionInfo, setRegionInfoLoading, setRegionInfoError, setRegionBoundary, pushRecentRegion]);

  const handleSelectRecent = useCallback((recent: { id: string; name: string }) => {
    // Build a minimal RegionSearchResult-compatible call via name lookup
    setSuppressSearch(true);
    setQuery(recent.name);
    clearResults();
    Keyboard.dismiss();
    setFocused(false);

    const currentBoundaryRequestId = ++boundaryRequestIdRef.current;

    pushRecentRegion({ id: recent.id, name: recent.name });
    setSelectedRegion(recent.id);
    setLoading(true);
    setRegionInfoLoading(true);

    apiService.getRegionInfo(recent.id, true)
      .then((response) => {
        if (!response.success || !response.data) {
          setRegionInfoError('No climate data available for this region');
          return;
        }
        const info = response.data;
        const overview = formatClimateOverview(info.current_climate, useMapStore.getState().activeLayer);
        const deltas = getDeltasForType(info.type);
        setRegion({
          latitude: info.location.latitude,
          longitude: info.location.longitude,
          latitudeDelta: deltas.latitudeDelta,
          longitudeDelta: deltas.longitudeDelta,
        });
        const targetLevel = inferMapLevel(info.type);
        if (targetLevel) {
          setMapLevel(targetLevel);
        }
        openRegionInfo({
          regionId: info.id,
          regionName: info.name,
          regionType: info.type,
          latitude: info.location.latitude,
          longitude: info.location.longitude,
          climate: overview,
        });
      })
      .catch((err) => {
        console.error('Failed to load region info', err);
        setRegionInfoError('Failed to load region information');
      });

    loadRegionBoundary(recent.id)
      .then((boundary) => {
        if (boundaryRequestIdRef.current !== currentBoundaryRequestId) {
          return;
        }
        setRegionBoundary(boundary);
      })
      .catch((err) => {
        console.error('Failed to load region boundary', err);
      });
  }, [setRegion, setMapLevel, clearResults, setSelectedRegion, setLoading, openRegionInfo, setRegionInfoLoading, setRegionInfoError, setRegionBoundary, pushRecentRegion]);

  const handleChangeText = useCallback((text: string) => {
    setSuppressSearch(false);
    setQuery(text);
    if (text.trim().length === 0) {
      boundaryRequestIdRef.current += 1;
      closeRegionInfo();
      setRegionBoundary(null);
    }
  }, [closeRegionInfo, setRegionBoundary]);

  const handleClear = useCallback(() => {
    setSuppressSearch(false);
    setQuery('');
    clearResults();
    boundaryRequestIdRef.current += 1;
    closeRegionInfo();
    setRegionBoundary(null);
  }, [clearResults, closeRegionInfo, setRegionBoundary]);

  const handleCancel = useCallback(() => {
    handleClear();
    setFocused(false);
    Keyboard.dismiss();
    inputRef.current?.blur();
  }, [handleClear]);

  const hasQuery = query.trim().length > 0;
  // Show suggestions whenever data is available (preserves original behaviour
  // so tests that inject data without simulating focus still work).
  const showSuggestions = data.length > 0;
  // Show recents only when focused and input is empty (or as secondary section
  // below suggestions when focused with a query).
  const showRecents = focused && recentRegions.length > 0;
  const showDropdown = showSuggestions || showRecents;

  return (
    <View style={[styles.container, style]}>
      <View style={styles.inputContainer}>
        <Icon name="magnify" size={18} color={PALETTE.muted} style={styles.magnifyIcon} />
        <TextInput
          ref={inputRef}
          style={styles.input}
          value={query}
          placeholder="Search location"
          placeholderTextColor={PALETTE.muted}
          onChangeText={handleChangeText}
          onFocus={() => setFocused(true)}
          onBlur={() => {
            // Small delay so taps on suggestions register before blur hides them
            setTimeout(() => setFocused(false), 150);
          }}
          accessibilityLabel="Region search"
          returnKeyType="search"
        />
        {loading && <ActivityIndicator style={styles.indicator} size="small" color={PALETTE.muted} />}
        {!loading && hasQuery && (
          <TouchableOpacity style={styles.clearButton} onPress={handleClear} accessibilityLabel="Clear search">
            <Icon name="close" size={12} color={PALETTE.muted} />
          </TouchableOpacity>
        )}
        {focused && (
          <TouchableOpacity style={styles.cancelButton} onPress={handleCancel} accessibilityLabel="Cancel search">
            <Text style={styles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        )}
      </View>

      {!loading && error && <Text style={styles.errorText}>{error}</Text>}

      {showDropdown && (
        <View style={styles.resultsContainer}>
          {/* Suggestions section — shown when data is available */}
          {showSuggestions && (
            <>
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionHeaderLeft}>SUBURBS · QUEENSLAND</Text>
                <Text style={styles.sectionHeaderRight}>{data.length} matches</Text>
              </View>
              <FlatList
                keyboardShouldPersistTaps="handled"
                data={data}
                keyExtractor={(item) => item.id}
                renderItem={({ item }) => (
                  <SuggestionItem item={item} query={query} onPress={handleSelect} />
                )}
                ItemSeparatorComponent={() => <View style={styles.separator} />}
                scrollEnabled={false}
              />
            </>
          )}

          {/* Divider between suggestions and recents when both shown */}
          {showSuggestions && showRecents && (
            <View style={styles.sectionDivider} />
          )}

          {/* Recent section — only shown when focused */}
          {showRecents && (
            <>
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionHeaderLeft}>RECENT</Text>
              </View>
              {recentRegions.map((recent, idx) => (
                <React.Fragment key={recent.id}>
                  {idx > 0 && <View style={styles.separator} />}
                  <RecentItem recent={recent} onPress={handleSelectRecent} />
                </React.Fragment>
              ))}
            </>
          )}
        </View>
      )}
    </View>
  );
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const getDeltasForType = (type: string) => {
  switch (type) {
    case 'ssc':
    case 'suburb':
      return { latitudeDelta: 0.05, longitudeDelta: 0.05 };
    case 'postcode':
      return { latitudeDelta: 0.08, longitudeDelta: 0.08 };
    case 'city':
      return { latitudeDelta: 0.15, longitudeDelta: 0.15 };
    case 'lga':
    default:
      return { latitudeDelta: 0.8, longitudeDelta: 0.8 };
  }
};

const inferMapLevel = (type: string) => {
  if (type === 'ssc' || type === 'suburb' || type === 'postcode') {
    return 'ssc' as const;
  }
  if (type === 'lga') {
    return 'coarse' as const;
  }
  return undefined;
};

const formatRegionMeta = (item: RegionSearchResult): string => {
  const parts: string[] = [];
  parts.push(item.state);
  parts.push(item.type.toUpperCase());
  if (item.population) {
    parts.push(`Population ${item.population.toLocaleString()}`);
  }
  return parts.join(' · ').toUpperCase();
};

// Split text into [before, match, after] for highlight rendering
const splitHighlight = (text: string, query: string): [string, string, string] => {
  if (!query) {
    return [text, '', ''];
  }
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) {
    return [text, '', ''];
  }
  return [text.slice(0, idx), text.slice(idx, idx + query.length), text.slice(idx + query.length)];
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const SuggestionItem: React.FC<{
  item: RegionSearchResult;
  query: string;
  onPress: (item: RegionSearchResult) => void;
}> = ({ item, query, onPress }) => {
  const [before, match, after] = splitHighlight(item.name, query);
  return (
    <TouchableOpacity style={styles.resultItem} onPress={() => onPress(item)}>
      <View style={styles.pinTile}>
        <Icon name="map-marker" size={16} color={PALETTE.accent} />
      </View>
      <View style={styles.resultBody}>
        <Text style={styles.resultName} numberOfLines={1}>
          {before}
          {match ? (
            <Text style={styles.resultNameHighlight}>{match}</Text>
          ) : null}
          {after}
        </Text>
        <Text style={styles.resultMeta} numberOfLines={1}>{formatRegionMeta(item)}</Text>
      </View>
      <Icon name="chevron-right" size={14} color={PALETTE.faint} />
    </TouchableOpacity>
  );
};

const RecentItem: React.FC<{
  recent: { id: string; name: string };
  onPress: (recent: { id: string; name: string }) => void;
}> = ({ recent, onPress }) => (
  <TouchableOpacity style={styles.resultItem} onPress={() => onPress(recent)}>
    <Icon name="clock-outline" size={16} color={PALETTE.muted} style={styles.recentIcon} />
    <View style={styles.resultBody}>
      <Text style={styles.recentName} numberOfLines={1}>{recent.name}</Text>
    </View>
    <Icon name="chevron-right" size={14} color={PALETTE.faint} />
  </TouchableOpacity>
);

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignSelf: 'flex-start',
    position: 'relative',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: PALETTE.surface,
    borderRadius: RADII.control,
    paddingLeft: 14,
    paddingRight: 14,
    height: 46,
    borderWidth: 1,
    borderColor: PALETTE.border,
    ...Platform.select({
      ios: {
        shadowColor: '#0D1220',
        shadowOpacity: 0.10,
        shadowOffset: { width: 0, height: 8 },
        shadowRadius: 24,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  magnifyIcon: {
    marginRight: 8,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: PALETTE.fg,
    fontWeight: '500',
    letterSpacing: -0.075,
    padding: 0,
  },
  indicator: {
    marginLeft: 8,
  },
  clearButton: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: PALETTE.surface3,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 6,
  },
  cancelButton: {
    paddingVertical: 8,
    paddingLeft: 10,
    marginLeft: 4,
  },
  cancelText: {
    fontSize: 14,
    fontWeight: '500',
    color: PALETTE.accent,
  },
  errorText: {
    position: 'absolute',
    top: 54,
    left: 0,
    fontSize: 12,
    color: PALETTE.hazard,
  },
  resultsContainer: {
    position: 'absolute',
    top: 54,
    left: 0,
    right: 0,
    zIndex: 1000,
    borderRadius: RADII.card,
    backgroundColor: PALETTE.surface,
    borderWidth: 1,
    borderColor: PALETTE.border,
    overflow: 'hidden',
    ...Platform.select({
      ios: {
        shadowColor: '#0D1220',
        shadowOpacity: 0.10,
        shadowOffset: { width: 0, height: 8 },
        shadowRadius: 24,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 6,
  },
  sectionHeaderLeft: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.66,
    color: PALETTE.muted,
    textTransform: 'uppercase',
  },
  sectionHeaderRight: {
    fontSize: 11,
    color: PALETTE.fg2,
  },
  resultItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 14,
    gap: 10,
  },
  pinTile: {
    width: 32,
    height: 32,
    borderRadius: RADII.chip,
    backgroundColor: PALETTE.accentSoft,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  recentIcon: {
    width: 32,
    textAlign: 'center',
    flexShrink: 0,
  },
  resultBody: {
    flex: 1,
    flexDirection: 'column',
  },
  resultName: {
    fontSize: 16,
    fontWeight: '600',
    color: PALETTE.fg,
    letterSpacing: -0.16,
    lineHeight: 20,
  },
  resultNameHighlight: {
    backgroundColor: 'rgba(11,134,200,0.16)',
  },
  resultMeta: {
    fontSize: 12,
    color: PALETTE.muted,
    letterSpacing: 0.24,
    textTransform: 'uppercase',
    marginTop: 1,
  },
  recentName: {
    fontSize: 15,
    fontWeight: '500',
    color: PALETTE.fg2,
  },
  separator: {
    height: 1,
    backgroundColor: PALETTE.border,
    marginHorizontal: 14,
  },
  sectionDivider: {
    height: 1,
    backgroundColor: PALETTE.border,
    marginTop: 4,
  },
});

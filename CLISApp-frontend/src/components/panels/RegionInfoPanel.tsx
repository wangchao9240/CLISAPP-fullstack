import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { useMapStore } from '../../store/mapStore';
import { useFavoritesStore } from '../../store/favoritesStore';
import { RegionClimateStat } from '../../types/region.types';

const formatValue = (stat: RegionClimateStat | null) => {
  if (!stat) return '--';
  const value = Number.isFinite(stat.value) ? stat.value.toFixed(stat.layer === 'humidity' ? 0 : 1) : '--';
  return `${value} ${stat.unit ?? ''}`.trim();
};

const getCategoryColor = (category?: string): string => {
  if (!category) return '#6B7280';
  
  const lowerCategory = category.toLowerCase();
  
  // PM2.5 categories
  if (lowerCategory.includes('good')) return '#10B981';
  if (lowerCategory.includes('moderate')) return '#F59E0B';
  if (lowerCategory.includes('unhealthy for sensitive')) return '#F97316';
  if (lowerCategory.includes('unhealthy')) return '#EF4444';
  if (lowerCategory.includes('very unhealthy')) return '#DC2626';
  if (lowerCategory.includes('hazardous')) return '#7C2D12';
  
  // UV Index categories
  if (lowerCategory.includes('low')) return '#10B981';
  if (lowerCategory.includes('medium') || lowerCategory.includes('moderate')) return '#F59E0B';
  if (lowerCategory.includes('high')) return '#F97316';
  if (lowerCategory.includes('very high')) return '#EF4444';
  if (lowerCategory.includes('extreme')) return '#DC2626';
  
  // Temperature categories
  if (lowerCategory.includes('cold')) return '#3B82F6';
  if (lowerCategory.includes('cool')) return '#60A5FA';
  if (lowerCategory.includes('mild')) return '#10B981';
  if (lowerCategory.includes('warm')) return '#F59E0B';
  if (lowerCategory.includes('hot')) return '#EF4444';
  
  // Humidity categories
  if (lowerCategory.includes('dry')) return '#F59E0B';
  if (lowerCategory.includes('comfortable')) return '#10B981';
  if (lowerCategory.includes('humid')) return '#3B82F6';
  
  // Precipitation categories
  if (lowerCategory.includes('none') || lowerCategory.includes('no rain')) return '#6B7280';
  if (lowerCategory.includes('light')) return '#60A5FA';
  if (lowerCategory.includes('moderate')) return '#3B82F6';
  if (lowerCategory.includes('heavy')) return '#1E40AF';
  
  return '#6B7280';
};

export const RegionInfoPanel: React.FC = () => {
  const { regionInfo, closeRegionInfo } = useMapStore();
  const { addFavorite, isFavorite, removeFavorite } = useFavoritesStore();

  if (!regionInfo.visible) {
    return null;
  }

  const { regionId, regionName, regionType, climate, loading, error } = regionInfo;
  const primary = climate?.primary ?? null;
  const isMarked = regionId ? isFavorite(regionId) : false;

  const handleMarkLocation = () => {
    if (!regionId || !regionName || !regionType) return;

    if (isMarked) {
      removeFavorite(regionId);
      return;
    }

    addFavorite({
      regionId,
      regionName,
      regionType,
      timestamp: new Date().toISOString(),
    });

  };

  const categoryColor = getCategoryColor(primary?.category);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.regionName}>{regionName}</Text>
          <Text style={styles.regionMeta}>{regionType === 'suburb' ? 'Suburb' : 'LGA'}</Text>
        </View>
        <View style={styles.headerRight}>
          <TouchableOpacity 
            style={[styles.markButton, isMarked && styles.markButtonActive]}
            onPress={handleMarkLocation}
          >
            <Text style={[styles.markIcon, isMarked && styles.markIconActive]}>
              {isMarked ? '★' : '☆'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.closeButton} onPress={closeRegionInfo}>
            <Text style={styles.closeText}>×</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Primary climate data - matches Figma prototype */}
      <View style={styles.primaryBlock}>
        <Text style={styles.primaryTitle}>{primary?.name ?? 'Environmental Data'}</Text>
        <View style={styles.primaryValueRow}>
          <Text style={styles.primaryValue}>{formatValue(primary)}</Text>
          {primary?.category && (
            <View style={[styles.categoryBadge, { backgroundColor: `${categoryColor}15` }]}>
              <Text style={[styles.categoryText, { color: categoryColor }]}>
                {primary.category}
              </Text>
            </View>
          )}
        </View>
        {primary?.description && (
          <Text style={styles.primaryDescription}>{primary.description}</Text>
        )}
      </View>

      {/* Loading state */}
      {loading && (
        <View style={styles.loadingBlock}>
          <View style={styles.skeletonTitle} />
          <View style={styles.skeletonValue} />
        </View>
      )}

      {/* Footer with timestamp */}
      <View style={styles.footer}>
        {!loading && error && <Text style={styles.errorText}>{error}</Text>}
        {!loading && !error && primary?.lastUpdated && (
          <Text style={styles.timestampText}>
            Updated: {new Date(primary.lastUpdated).toLocaleString('en-AU', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </Text>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 999,
    backgroundColor: 'rgba(255,255,255,0.97)',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 28,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
    elevation: 10,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  headerLeft: {
    flex: 1,
  },
  headerRight: {
    flexDirection: 'row',
    gap: 8,
  },
  regionName: {
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
    letterSpacing: -0.4,
  },
  regionMeta: {
    marginTop: 4,
    fontSize: 13,
    fontWeight: '500',
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  markButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.04)',
  },
  markButtonActive: {
    backgroundColor: 'rgba(251, 191, 36, 0.15)',
  },
  markIcon: {
    fontSize: 20,
    color: '#9CA3AF',
  },
  markIconActive: {
    color: '#F59E0B',
  },
  closeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.04)',
  },
  closeText: {
    fontSize: 24,
    color: '#6B7280',
    marginTop: -2,
  },
  primaryBlock: {
    backgroundColor: '#F9FAFB',
    borderRadius: 16,
    paddingVertical: 20,
    paddingHorizontal: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.04)',
  },
  primaryTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  primaryValueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 8,
  },
  primaryValue: {
    fontSize: 36,
    fontWeight: '700',
    color: '#111827',
    letterSpacing: -1,
  },
  categoryBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  categoryText: {
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  primaryDescription: {
    fontSize: 13,
    color: '#6B7280',
    lineHeight: 18,
    marginTop: 4,
  },
  loadingBlock: {
    backgroundColor: '#F9FAFB',
    borderRadius: 16,
    paddingVertical: 20,
    paddingHorizontal: 20,
    marginBottom: 16,
  },
  skeletonTitle: {
    width: 120,
    height: 14,
    borderRadius: 7,
    backgroundColor: 'rgba(0,0,0,0.08)',
    marginBottom: 12,
  },
  skeletonValue: {
    width: 160,
    height: 36,
    borderRadius: 8,
    backgroundColor: 'rgba(0,0,0,0.06)',
  },
  footer: {
    paddingTop: 4,
  },
  timestampText: {
    fontSize: 12,
    color: '#9CA3AF',
    fontWeight: '500',
  },
  errorText: {
    fontSize: 13,
    color: '#DC2626',
    fontWeight: '500',
  },
});
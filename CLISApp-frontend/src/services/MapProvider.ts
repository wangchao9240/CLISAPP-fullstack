// Map provider abstraction for easy switching between React Native Maps and MapLibre
import { Region } from '../types/map.types';
import { ClimateLayer, MapLevel } from '../types/climate.types';

export interface MapProviderInterface {
  // Core map operations
  setRegion(region: Region): void;
  animateToRegion(region: Region, duration?: number): void;
  
  // Layer management
  setTileLayer(layer: ClimateLayer, level: MapLevel): void;
  setTileOpacity(opacity: number): void;
  
  // Interaction
  highlightArea(coordinates: number[][]): void;
  clearHighlight(): void;
  
  // Event handling
  onRegionChange(callback: (region: Region) => void): void;
  onLongPress(callback: (coordinate: { latitude: number; longitude: number }) => void): void;
  emitLongPress(coordinate: { latitude: number; longitude: number }): void;
  
  // Utility
  getVisibleBounds(): {northeast: {lat: number, lng: number}, southwest: {lat: number, lng: number}};
  
  // Cleanup
  destroy(): void;
}

export interface MapConfig {
  provider: 'react-native-maps' | 'maplibre';
  apiKey?: string;
  styleUrl?: string;
  tileServerUrl: string;
}

// Factory for creating map providers
export class MapProviderFactory {
  static create(config: MapConfig): MapProviderInterface {
    switch (config.provider) {
      case 'react-native-maps':
        return new ReactNativeMapsProvider(config);
      case 'maplibre':
        return new MapLibreProvider(config);
      default:
        throw new Error(`Unsupported map provider: ${config.provider}`);
    }
  }
}

// React Native Maps implementation
class ReactNativeMapsProvider implements MapProviderInterface {
  private mapRef: any;
  private config: MapConfig;
  private currentTileUrl: string = '';
  private regionChangeCallback?: (region: Region) => void;
  private longPressCallback?: (coordinate: any) => void;

  constructor(config: MapConfig) {
    this.config = config;
  }

  setMapRef(ref: any) {
    this.mapRef = ref;
  }

  setRegion(region: Region): void {
    // Implementation handled by React Native Maps component
  }

  animateToRegion(region: Region, duration: number = 1000): void {
    this.mapRef?.animateToRegion(region, duration);
  }

  setTileLayer(layer: ClimateLayer, level: MapLevel): void {
    this.currentTileUrl = `${this.config.tileServerUrl}/${layer}/{z}/{x}/{y}.png`;
  }

  setTileOpacity(opacity: number): void {
    // Handled by UrlTile component opacity prop
  }

  highlightArea(coordinates: number[][]): void {
    // Implementation needed - add Polygon overlay
  }

  clearHighlight(): void {
    // Implementation needed - remove Polygon overlay
  }

  onRegionChange(callback: (region: Region) => void): void {
    this.regionChangeCallback = callback;
  }

  onLongPress(callback: (coordinate: any) => void): void {
    this.longPressCallback = callback;
  }

  emitLongPress(coordinate: { latitude: number; longitude: number }): void {
    this.longPressCallback?.(coordinate);
  }

  getVisibleBounds() {
    // Implementation needed
    return {
      northeast: { lat: 0, lng: 0 },
      southwest: { lat: 0, lng: 0 }
    };
  }

  getTileUrl(): string {
    return this.currentTileUrl;
  }

  destroy(): void {
    this.mapRef = null;
    this.regionChangeCallback = undefined;
    this.longPressCallback = undefined;
  }
}

// MapLibre implementation (future)
class MapLibreProvider implements MapProviderInterface {
  private map: any;
  private config: MapConfig;

  constructor(config: MapConfig) {
    this.config = config;
  }

  setRegion(region: Region): void {
    this.map?.flyTo({
      center: [region.longitude, region.latitude],
      zoom: this.calculateZoom(region),
    });
  }

  animateToRegion(region: Region, duration: number = 1000): void {
    this.map?.flyTo({
      center: [region.longitude, region.latitude],
      zoom: this.calculateZoom(region),
      duration,
    });
  }

  setTileLayer(layer: ClimateLayer, level: MapLevel): void {
    const sourceId = 'climate-tiles';
    const layerId = 'climate-layer';
    
    // Remove existing layer
    if (this.map?.getLayer(layerId)) {
      this.map.removeLayer(layerId);
    }
    if (this.map?.getSource(sourceId)) {
      this.map.removeSource(sourceId);
    }

    // Add new tile source
    this.map?.addSource(sourceId, {
      type: 'raster',
      tiles: [`${this.config.tileServerUrl}/${layer}/{z}/{x}/{y}.png`],
      tileSize: 256,
    });

    // Add layer
    this.map?.addLayer({
      id: layerId,
      type: 'raster',
      source: sourceId,
    });
  }

  setTileOpacity(opacity: number): void {
    this.map?.setPaintProperty('climate-layer', 'raster-opacity', opacity);
  }

  highlightArea(coordinates: number[][]): void {
    const sourceId = 'highlight-source';
    const layerId = 'highlight-layer';

    // Remove existing highlight
    this.clearHighlight();

    // Add highlight polygon
    this.map?.addSource(sourceId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [coordinates],
        },
      },
    });

    this.map?.addLayer({
      id: layerId,
      type: 'line',
      source: sourceId,
      paint: {
        'line-color': '#007AFF',
        'line-width': 3,
      },
    });
  }

  clearHighlight(): void {
    if (this.map?.getLayer('highlight-layer')) {
      this.map.removeLayer('highlight-layer');
    }
    if (this.map?.getSource('highlight-source')) {
      this.map.removeSource('highlight-source');
    }
  }

  onRegionChange(callback: (region: Region) => void): void {
    this.map?.on('moveend', () => {
      const center = this.map.getCenter();
      const bounds = this.map.getBounds();
      const region: Region = {
        latitude: center.lat,
        longitude: center.lng,
        latitudeDelta: bounds.getNorth() - bounds.getSouth(),
        longitudeDelta: bounds.getEast() - bounds.getWest(),
      };
      callback(region);
    });
  }

  onLongPress(callback: (coordinate: any) => void): void {
    this.map?.on('longclick', (e: any) => {
      callback({
        latitude: e.lngLat.lat,
        longitude: e.lngLat.lng,
      });
    });
  }

  emitLongPress(coordinate: { latitude: number; longitude: number }): void {
    // MapLibre will have its own event wiring; emitLongPress is a no-op when
    // the underlying map already handles callbacks internally.
    // This keeps the interface consistent across providers.
    // eslint-disable-next-line @typescript-eslint/no-empty-function
  }

  getVisibleBounds() {
    const bounds = this.map?.getBounds();
    return {
      northeast: { lat: bounds.getNorth(), lng: bounds.getEast() },
      southwest: { lat: bounds.getSouth(), lng: bounds.getWest() },
    };
  }

  private calculateZoom(region: Region): number {
    // Convert latitudeDelta to zoom level
    return Math.round(Math.log(360 / region.latitudeDelta) / Math.LN2);
  }

  destroy(): void {
    this.map?.remove();
    this.map = null;
  }
}

export { ReactNativeMapsProvider, MapLibreProvider };

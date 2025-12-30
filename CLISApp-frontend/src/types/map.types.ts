// Map-related types for CLISApp
export interface Region {
  latitude: number;
  longitude: number;
  latitudeDelta: number;
  longitudeDelta: number;
}

export interface TileConfig {
  urlTemplate: string;
  maximumZ: number;
  minimumZ: number;
  opacity?: number;
}

export interface MapViewState {
  region: Region;
  isLoading: boolean;
  error?: string;
}

export interface SearchResult {
  id: string;
  name: string;
  location: {
    latitude: number;
    longitude: number;
  };
  type: 'lga' | 'suburb' | 'postcode' | 'city';
}

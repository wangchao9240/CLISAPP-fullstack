import React from 'react';
import { act, create } from 'react-test-renderer';

jest.mock('../../../store/mapStore', () => ({
  useMapStore: jest.fn(),
}));

jest.mock('../../../store/settingsStore', () => ({
  useSettingsStore: jest.fn(),
}));

jest.mock('../../../hooks/useApi', () => ({
  fetchRegionInfoByCoordinates: jest.fn(),
  formatClimateOverview: jest.fn(),
}));

jest.mock('../OpenStreetMap', () => ({
  OpenStreetMap: () => null,
}));

jest.mock('../../../services/MapProvider', () => ({
  MapProviderFactory: {
    create: jest.fn(),
  },
}));

const { UniversalMap } = require('../UniversalMap');
const { useMapStore } = require('../../../store/mapStore');
const { useSettingsStore } = require('../../../store/settingsStore');
const { MapProviderFactory } = require('../../../services/MapProvider');

const mockUseMapStore = useMapStore as jest.Mock;
const mockUseSettingsStore = useSettingsStore as jest.Mock;
const mockCreateProvider = MapProviderFactory.create as jest.Mock;

describe('UniversalMap', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('does not imperatively animate just because selectedRegionId is set', async () => {
    const provider = {
      animateToRegion: jest.fn(),
      setTileLayer: jest.fn(),
      onRegionChange: jest.fn(),
      onLongPress: jest.fn(),
      destroy: jest.fn(),
    };

    mockUseSettingsStore.mockReturnValue({
      mapProvider: 'react-native-maps',
      tileServerUrl: 'https://tiles.example.com',
    });
    mockUseMapStore.mockReturnValue({
      region: {
        latitude: -27.47,
        longitude: 153.02,
        latitudeDelta: 0.05,
        longitudeDelta: 0.05,
      },
      activeLayer: 'temperature',
      mapLevel: 'ssc',
      setRegion: jest.fn(),
      selectedRegionId: 'region-1',
      setError: jest.fn(),
      setSelectedRegion: jest.fn(),
      openRegionInfo: jest.fn(),
      setRegionInfoLoading: jest.fn(),
      setRegionInfoError: jest.fn(),
    });
    mockCreateProvider.mockReturnValue(provider);

    await act(async () => {
      create(<UniversalMap />);
      await Promise.resolve();
    });

    expect(provider.animateToRegion).not.toHaveBeenCalled();
  });
});

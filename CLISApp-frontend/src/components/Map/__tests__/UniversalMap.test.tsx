import React from 'react';
import { Animated } from 'react-native';
import { act, create } from 'react-test-renderer';

let mockBottomSheetModalProps: any;

jest.mock('../../../store/mapStore', () => ({
  useMapStore: jest.fn(),
}));

jest.mock('../../../store/favoritesStore', () => ({
  useFavoritesStore: jest.fn(),
}));

jest.mock('../../../store/settingsStore', () => ({
  useSettingsStore: jest.fn(),
}));

jest.mock('../../../hooks/useApi', () => ({
  fetchRegionInfoByCoordinates: jest.fn(),
  formatClimateOverview: jest.fn(),
}));

jest.mock('../../../constants/climateData', () => ({
  formatBadgeText: jest.fn(() => 'Test badge'),
  getActiveClimateStat: jest.fn(() => null),
}));

jest.mock('../OpenStreetMap', () => ({
  OpenStreetMap: () => null,
}));

jest.mock('../../../services/MapProvider', () => ({
  MapProviderFactory: {
    create: jest.fn(),
  },
}));

jest.mock('@gorhom/bottom-sheet', () => {
  const React = require('react');

  const BottomSheetModal = React.forwardRef((props: any, ref: any) => {
    mockBottomSheetModalProps = props;
    React.useImperativeHandle(ref, () => ({
      present: jest.fn(),
      dismiss: jest.fn(),
    }));

    return <>{props.children}</>;
  });

  return {
    BottomSheetModal,
    BottomSheetView: ({ children }: any) => <>{children}</>,
    BottomSheetScrollView: ({ children }: any) => <>{children}</>,
    BottomSheetBackdrop: () => null,
  };
});

jest.mock('react-native-paper', () => {
  const React = require('react');

  return {
    Snackbar: (props: any) => React.createElement('Snackbar', props, props.children),
  };
});

jest.mock('react-native-vector-icons/MaterialCommunityIcons', () => {
  const React = require('react');

  return (props: any) => React.createElement('Icon', props);
});

const { UniversalMap } = require('../UniversalMap');
const { HealthBottomSheet } = require('../../panels/HealthBottomSheet');
const { useMapStore } = require('../../../store/mapStore');
const { useFavoritesStore } = require('../../../store/favoritesStore');
const { Snackbar } = require('react-native-paper');
const { useSettingsStore } = require('../../../store/settingsStore');
const { fetchRegionInfoByCoordinates, formatClimateOverview } = require('../../../hooks/useApi');
const { MapProviderFactory } = require('../../../services/MapProvider');

const mockUseMapStore = useMapStore as jest.Mock;
const mockUseFavoritesStore = useFavoritesStore as jest.Mock;
const mockUseSettingsStore = useSettingsStore as jest.Mock;
const mockFetchRegionInfoByCoordinates = fetchRegionInfoByCoordinates as jest.Mock;
const mockFormatClimateOverview = formatClimateOverview as jest.Mock;
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

  it('passes fetched coordinates into region info on long press', async () => {
    const provider = {
      animateToRegion: jest.fn(),
      setTileLayer: jest.fn(),
      onRegionChange: jest.fn(),
      onLongPress: jest.fn(),
      destroy: jest.fn(),
    };
    const openRegionInfo = jest.fn();
    const setRegionInfoLoading = jest.fn();
    const setSelectedRegion = jest.fn();

    mockUseSettingsStore.mockReturnValue({
      mapProvider: 'react-native-maps',
      tileServerUrl: 'https://tiles.example.com',
    });
    mockUseMapStore.mockReturnValue({
      activeLayer: 'temperature',
      mapLevel: 'ssc',
      setRegion: jest.fn(),
      setError: jest.fn(),
      setSelectedRegion,
      openRegionInfo,
      setRegionInfoLoading,
      setRegionInfoError: jest.fn(),
    });
    mockCreateProvider.mockReturnValue(provider);
    mockFetchRegionInfoByCoordinates.mockResolvedValue({
      id: 'ssc-1',
      name: 'Fortitude Valley',
      type: 'ssc',
      location: {
        latitude: -27.457,
        longitude: 153.034,
      },
      current_climate: { temperature: 29 },
    });
    mockFormatClimateOverview.mockReturnValue({ summary: 'Hot' });

    await act(async () => {
      create(<UniversalMap />);
      await Promise.resolve();
    });

    await act(async () => {
      await provider.onLongPress.mock.calls[0][0]({
        latitude: -27.47,
        longitude: 153.02,
      });
    });

    expect(setRegionInfoLoading).toHaveBeenCalledWith(true);
    expect(openRegionInfo).toHaveBeenCalledWith({
      regionId: 'ssc-1',
      regionName: 'Fortitude Valley',
      regionType: 'ssc',
      climate: { summary: 'Hot' },
      latitude: -27.457,
      longitude: 153.034,
    });
    expect(setSelectedRegion).toHaveBeenCalledWith('ssc-1');
  });
});

describe('HealthBottomSheet', () => {
  let springStart: jest.Mock;
  let springSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    springStart = jest.fn((callback?: () => void) => callback?.());
    mockBottomSheetModalProps = undefined;
    springSpy = jest
      .spyOn(Animated, 'spring')
      .mockReturnValue({ start: springStart } as any);
  });

  afterEach(() => {
    springSpy.mockRestore();
  });

  it('allows saving SSC regions as favorites with coordinates and animation', () => {
    const addFavorite = jest.fn();
    const removeFavorite = jest.fn();
    const restoreFavorite = jest.fn();

    mockUseMapStore.mockReturnValue({
      regionInfo: {
        visible: true,
        regionId: 'ssc-1',
        regionName: 'Fortitude Valley',
        regionType: 'ssc',
        climate: null,
        latitude: -27.457,
        longitude: 153.034,
        loading: false,
        error: null,
      },
      activeLayer: 'temperature',
      closeRegionInfo: jest.fn(),
    });
    mockUseFavoritesStore.mockReturnValue({
      isFavorite: jest.fn(() => false),
      addFavorite,
      removeFavorite,
      restoreFavorite,
    });

    const renderer = create(<HealthBottomSheet />);
    const favoriteButton = renderer.root.find((node) => typeof node.props.onPress === 'function');

    act(() => {
      favoriteButton.props.onPress();
    });

    expect(favoriteButton.props.disabled).not.toBe(true);
    expect(addFavorite).toHaveBeenCalledWith({
      regionId: 'ssc-1',
      regionName: 'Fortitude Valley',
      regionType: 'ssc',
      latitude: -27.457,
      longitude: 153.034,
      timestamp: expect.any(String),
    });
    expect(springSpy).toHaveBeenCalled();
    expect(springStart).toHaveBeenCalled();
  });

  it('shows an undo snackbar when removing a favorite and restores the saved item', () => {
    const favorite = {
      regionId: 'ssc-1',
      regionName: 'Fortitude Valley',
      regionType: 'ssc',
      latitude: -27.457,
      longitude: 153.034,
      timestamp: '2026-03-22T04:00:00.000Z',
    };
    const removeFavorite = jest.fn();
    const restoreFavorite = jest.fn();

    mockUseMapStore.mockReturnValue({
      regionInfo: {
        visible: true,
        regionId: favorite.regionId,
        regionName: favorite.regionName,
        regionType: favorite.regionType,
        climate: null,
        latitude: favorite.latitude,
        longitude: favorite.longitude,
        loading: false,
        error: null,
      },
      activeLayer: 'temperature',
      closeRegionInfo: jest.fn(),
    });
    mockUseFavoritesStore.mockReturnValue({
      isFavorite: jest.fn(() => true),
      addFavorite: jest.fn(),
      removeFavorite,
      restoreFavorite,
      getFavorite: jest.fn(() => favorite),
    });

    const renderer = create(<HealthBottomSheet />);
    const favoriteButton = renderer.root.find((node) => typeof node.props.onPress === 'function');

    act(() => {
      favoriteButton.props.onPress();
    });

    const snackbar = renderer.root.findByType(Snackbar);

    expect(removeFavorite).toHaveBeenCalledWith('ssc-1');
    expect(snackbar.props.visible).toBe(true);
    expect(snackbar.props.children).toBe('Deleted');
    expect(snackbar.props.action.label).toBe('Undo');

    act(() => {
      snackbar.props.action.onPress();
    });

    expect(restoreFavorite).toHaveBeenCalledWith(favorite);
  });

  it('waits until modal dismiss to clear region data after a swipe close', () => {
    const closeRegionInfo = jest.fn();
    const clearRegionInfo = jest.fn();
    (mockUseMapStore as any).getState = jest.fn(() => ({
      regionInfo: {
        visible: false,
      },
    }));

    mockUseMapStore.mockReturnValue({
      regionInfo: {
        visible: true,
        regionId: 'ssc-1',
        regionName: 'Fortitude Valley',
        regionType: 'ssc',
        climate: null,
        latitude: -27.457,
        longitude: 153.034,
        loading: false,
        error: null,
      },
      activeLayer: 'temperature',
      closeRegionInfo,
      clearRegionInfo,
    });
    mockUseFavoritesStore.mockReturnValue({
      isFavorite: jest.fn(() => false),
      addFavorite: jest.fn(),
      removeFavorite: jest.fn(),
      restoreFavorite: jest.fn(),
      getFavorite: jest.fn(),
    });

    create(<HealthBottomSheet />);

    act(() => {
      mockBottomSheetModalProps.onChange(-1);
    });

    expect(closeRegionInfo).toHaveBeenCalledTimes(1);
    expect(clearRegionInfo).not.toHaveBeenCalled();

    act(() => {
      mockBottomSheetModalProps.onDismiss();
    });

    expect(clearRegionInfo).toHaveBeenCalledTimes(1);
  });

  it('does not clear region data on dismiss if another region is already visible', () => {
    const clearRegionInfo = jest.fn();
    (mockUseMapStore as any).getState = jest.fn(() => ({
      regionInfo: {
        visible: true,
      },
    }));

    mockUseMapStore.mockReturnValue({
      regionInfo: {
        visible: true,
        regionId: 'ssc-2',
        regionName: 'Sunnybank Hills',
        regionType: 'ssc',
        climate: null,
        latitude: -27.58,
        longitude: 153.06,
        loading: false,
        error: null,
      },
      activeLayer: 'temperature',
      closeRegionInfo: jest.fn(),
      clearRegionInfo,
    });
    mockUseFavoritesStore.mockReturnValue({
      isFavorite: jest.fn(() => false),
      addFavorite: jest.fn(),
      removeFavorite: jest.fn(),
      restoreFavorite: jest.fn(),
      getFavorite: jest.fn(),
    });

    create(<HealthBottomSheet />);

    act(() => {
      mockBottomSheetModalProps.onDismiss();
    });

    expect(clearRegionInfo).not.toHaveBeenCalled();
  });
});

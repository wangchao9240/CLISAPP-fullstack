import React from 'react';
import { act, create } from 'react-test-renderer';

jest.mock('react-native-vector-icons/MaterialCommunityIcons', () => {
  const { Text } = require('react-native');
  return ({ name, ...props }: any) => <Text {...props}>{name}</Text>;
});

jest.mock('../../../hooks/useApi', () => ({
  useRegionSearch: jest.fn(),
  formatClimateOverview: jest.fn(),
}));

jest.mock('../../../store/mapStore', () => ({
  useMapStore: jest.fn(),
}));

jest.mock('../../../services/ApiService', () => ({
  apiService: {
    getRegionInfo: jest.fn(),
  },
}));

jest.mock('../../../services/boundaries/boundaryLoader', () => ({
  loadRegionBoundary: jest.fn(),
}));

const { RegionSearchBar } = require('../RegionSearchBar');
const { useRegionSearch, formatClimateOverview } = require('../../../hooks/useApi');
const { useMapStore } = require('../../../store/mapStore');
const { apiService } = require('../../../services/ApiService');
const { loadRegionBoundary } = require('../../../services/boundaries/boundaryLoader');

const mockUseRegionSearch = useRegionSearch as jest.Mock;
const mockFormatClimateOverview = formatClimateOverview as jest.Mock;
const mockUseMapStore = useMapStore as jest.Mock;
const mockGetRegionInfo = apiService.getRegionInfo as jest.Mock;
const mockLoadRegionBoundary = loadRegionBoundary as jest.Mock;

describe('RegionSearchBar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (mockUseMapStore as any).getState = jest.fn(() => ({
      activeLayer: 'temperature',
    }));
  });

  it('ignores stale boundary responses from earlier search selections', async () => {
    const openRegionInfo = jest.fn();
    const setRegionBoundary = jest.fn();
    const pushRecentRegion = jest.fn();

    mockUseMapStore.mockReturnValue({
      setRegion: jest.fn(),
      setMapLevel: jest.fn(),
      setSelectedRegion: jest.fn(),
      setLoading: jest.fn(),
      openRegionInfo,
      setRegionInfoLoading: jest.fn(),
      setRegionInfoError: jest.fn(),
      closeRegionInfo: jest.fn(),
      setRegionBoundary,
      pushRecentRegion,
      recentRegions: [],
    });

    const searchResults = [
      {
        id: 'region-older',
        name: 'Older Region',
        type: 'lga',
        state: 'QLD',
        population: 1000,
        location: { latitude: -27.47, longitude: 153.02 },
      },
      {
        id: 'region-newer',
        name: 'Newer Region',
        type: 'lga',
        state: 'QLD',
        population: 2000,
        location: { latitude: -27.57, longitude: 152.92 },
      },
    ];

    mockUseRegionSearch.mockReturnValue({
      data: searchResults,
      loading: false,
      error: null,
      searchRegions: jest.fn(),
      clearResults: jest.fn(),
    });

    mockGetRegionInfo.mockResolvedValue({
      success: true,
      data: {
        id: 'region-info',
        name: 'Region Info',
        type: 'lga',
        location: {
          latitude: -27.47,
          longitude: 153.02,
        },
        current_climate: { temperature: { value: 23, unit: 'C' } },
      },
    });
    mockFormatClimateOverview.mockReturnValue({ summary: 'Test climate' });

    const firstBoundaryResult = {
      regionId: 'region-older',
      polygons: [{ outline: [{ latitude: -27.5, longitude: 153.0 }] }],
      properties: { source: 'older' },
    };
    const secondBoundaryResult = {
      regionId: 'region-newer',
      polygons: [{ outline: [{ latitude: -27.6, longitude: 152.9 }] }],
      properties: { source: 'newer' },
    };

    let resolveFirstBoundary: (value: any) => void;
    let resolveSecondBoundary: (value: any) => void;
    const firstBoundaryPromise = new Promise((resolve) => {
      resolveFirstBoundary = resolve;
    });
    const secondBoundaryPromise = new Promise((resolve) => {
      resolveSecondBoundary = resolve;
    });

    mockLoadRegionBoundary
      .mockImplementationOnce(() => firstBoundaryPromise)
      .mockImplementationOnce(() => secondBoundaryPromise);

    const renderer = create(<RegionSearchBar />);
    const olderResult = renderer.root.find(
      (node) => typeof node.props.onPress === 'function' && node.props.item?.id === 'region-older'
    );
    const newerResult = renderer.root.find(
      (node) => typeof node.props.onPress === 'function' && node.props.item?.id === 'region-newer'
    );

    await act(async () => {
      olderResult.props.onPress(olderResult.props.item);
      newerResult.props.onPress(newerResult.props.item);
      await Promise.resolve();
    });

    await act(async () => {
      resolveSecondBoundary!(secondBoundaryResult);
      await Promise.resolve();
    });

    await act(async () => {
      resolveFirstBoundary!(firstBoundaryResult);
      await Promise.resolve();
    });

    expect(setRegionBoundary).toHaveBeenLastCalledWith(secondBoundaryResult);
    expect(openRegionInfo).toHaveBeenCalledWith({
      regionId: 'region-info',
      regionName: 'Region Info',
      regionType: 'lga',
      climate: { summary: 'Test climate' },
      latitude: -27.47,
      longitude: 153.02,
    });
  });
});

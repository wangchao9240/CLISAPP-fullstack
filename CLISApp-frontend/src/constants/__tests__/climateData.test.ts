import { formatBadgeText, getActiveClimateStat } from '../climateData';
import { RegionClimateOverview, RegionClimateStat } from '../../types/region.types';

describe('formatBadgeText', () => {
  it('formats all supported layers with value, unit, and category suffix', () => {
    expect(formatBadgeText(35, 'µg/m³', 'Moderate', 'pm25')).toBe('35 µg/m³ / Moderate Air Quality');
    expect(formatBadgeText(6.2, 'UVI', 'Moderate', 'uv')).toBe('6.2 UVI / Moderate UV Exposure');
    expect(formatBadgeText(28.5, '°C', 'High', 'temperature')).toBe('28.5 °C / High Temperature');
    expect(formatBadgeText(65, '%', 'Moderate', 'humidity')).toBe('65 % / Moderate Humidity');
    expect(formatBadgeText(2.5, 'mm/day', 'Low', 'precipitation')).toBe('2.5 mm/day / Low Rainfall');
  });

  it('falls back to category label when value or unit is missing', () => {
    expect(formatBadgeText(undefined, 'UVI', 'Moderate', 'uv')).toBe('Moderate UV Exposure');
    expect(formatBadgeText(6.2, undefined, 'Moderate', 'uv')).toBe('Moderate UV Exposure');
  });

  it('shows value and layer suffix when category is missing', () => {
    expect(formatBadgeText(28.5, '°C', undefined, 'temperature')).toBe('28.5 °C / Temperature');
  });

  it('shows only layer suffix when everything is undefined', () => {
    expect(formatBadgeText(undefined, undefined, undefined, 'humidity')).toBe('Humidity');
  });
});

describe('getActiveClimateStat', () => {
  const pm25Stat: RegionClimateStat = {
    layer: 'pm25',
    name: 'PM2.5 Concentration',
    value: 35,
    unit: 'µg/m³',
    category: 'Moderate',
  };

  const uvStat: RegionClimateStat = {
    layer: 'uv',
    name: 'UV Index',
    value: 6.2,
    unit: 'UVI',
    category: 'Moderate',
  };

  const temperatureStat: RegionClimateStat = {
    layer: 'temperature',
    name: '2m Temperature',
    value: 28.5,
    unit: '°C',
    category: 'High',
  };

  it('returns primary when primary matches the active layer', () => {
    const climate: RegionClimateOverview = {
      primary: pm25Stat,
      secondary: [uvStat, temperatureStat],
    };

    expect(getActiveClimateStat(climate, 'pm25')).toEqual(pm25Stat);
  });

  it('returns a matching secondary stat when primary does not match', () => {
    const climate: RegionClimateOverview = {
      primary: pm25Stat,
      secondary: [uvStat, temperatureStat],
    };

    expect(getActiveClimateStat(climate, 'uv')).toEqual(uvStat);
  });

  it('returns null when no stat matches the active layer', () => {
    const climate: RegionClimateOverview = {
      primary: pm25Stat,
      secondary: [uvStat],
    };

    expect(getActiveClimateStat(climate, 'humidity')).toBeNull();
  });

  it('returns null when climate overview is null', () => {
    expect(getActiveClimateStat(null, 'temperature')).toBeNull();
  });

  it('returns the current layer stat when switching away from the stored primary layer', () => {
    const climate: RegionClimateOverview = {
      primary: pm25Stat,
      secondary: [uvStat, temperatureStat],
    };

    expect(getActiveClimateStat(climate, 'uv')).toEqual(uvStat);
  });
});

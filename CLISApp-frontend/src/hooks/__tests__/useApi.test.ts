jest.mock('react-native-config', () => ({
  API_URL: 'http://localhost:8080',
}));

const { formatClimateOverview } = require('../useApi') as typeof import('../useApi');

describe('formatClimateOverview', () => {
  it('maps snake_case health risk fields into camelCase climate stats', () => {
    const overview = formatClimateOverview(
      {
        pm25: {
          layer: 'pm25',
          value: 35,
          unit: 'µg/m³',
          timestamp: '2026-03-17T12:00:00Z',
          category: 'Moderate',
          risk_level: 'Unhealthy',
          advice: 'Everyone should reduce outdoor activity.',
        },
      },
      'pm25',
    );

    expect(overview.primary).toMatchObject({
      layer: 'pm25',
      category: 'Moderate',
      riskLevel: 'Unhealthy',
      advice: 'Everyone should reduce outdoor activity.',
    });
  });

  it('normalizes null health risk fields to undefined', () => {
    const overview = formatClimateOverview(
      {
        uv: {
          layer: 'uv',
          value: 2,
          unit: 'UVI',
          timestamp: '2026-03-17T12:00:00Z',
          risk_level: null,
          advice: null,
        },
      },
      'uv',
    );

    expect(overview.primary).toMatchObject({
      layer: 'uv',
      riskLevel: undefined,
      advice: undefined,
    });
  });
});

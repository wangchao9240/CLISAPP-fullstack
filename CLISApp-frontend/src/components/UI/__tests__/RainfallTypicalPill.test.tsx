import React from 'react';
import { create } from 'react-test-renderer';
import { RainfallTypicalPill } from '../RainfallTypicalPill';

jest.mock('../../../../assets/data/climate_baseline.json', () => ({
  baselines: {},
}));

jest.mock(
  '../../../../assets/data/climate_baseline_daily.json',
  () => ({
    baselines: {
      ssc_A: {
        tmean: Array(366).fill(20),
        MT: Array(366).fill(30),
        mT: Array(366).fill(10),
        rf: Array(366).fill(2.6),
      },
    },
  }),
  { virtual: true },
);

describe('RainfallTypicalPill', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date(2026, 4, 8, 12));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders the static typical rainfall caption', () => {
    const renderer = create(<RainfallTypicalPill regionSscId="ssc_A" />);
    expect(renderer.toJSON()).toMatchSnapshot();
    renderer.unmount();
  });

  it('returns null when daily rainfall data is missing', () => {
    const renderer = create(<RainfallTypicalPill regionSscId="ssc_missing" />);
    expect(renderer.toJSON()).toBeNull();
    renderer.unmount();
  });
});

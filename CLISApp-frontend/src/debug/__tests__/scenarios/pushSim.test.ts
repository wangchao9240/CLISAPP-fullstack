import { Alert } from 'react-native';
import { firePushSimulated } from '../../scenarios/pushSim';
import { useDebugStore } from '../../debugStore';

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

jest.spyOn(Alert, 'alert').mockImplementation(() => {});

describe('firePushSimulated', () => {
  beforeEach(() => {
    useDebugStore.getState().resetAll();
    useDebugStore.setState({ telemetryTail: [], telemetryUnreadCount: 0 });
    (Alert.alert as jest.Mock).mockClear();
  });

  it('shows the heatwave template on first call', () => {
    firePushSimulated();

    expect(Alert.alert).toHaveBeenCalledWith(
      'Extreme Heat Warning',
      expect.stringContaining('Temperatures forecast'),
    );
  });

  it('rotates through smoke on second call and uv-extreme on third', () => {
    firePushSimulated();
    firePushSimulated();
    expect(Alert.alert).toHaveBeenLastCalledWith('Air Quality Alert', expect.any(String));

    firePushSimulated();
    expect(Alert.alert).toHaveBeenLastCalledWith('Extreme UV Alert', expect.any(String));
  });

  it('bumps pushRotationIndex on each call', () => {
    firePushSimulated();
    expect(useDebugStore.getState().pushRotationIndex).toBe(1);

    firePushSimulated();
    expect(useDebugStore.getState().pushRotationIndex).toBe(2);

    firePushSimulated();
    expect(useDebugStore.getState().pushRotationIndex).toBe(0);
  });
});

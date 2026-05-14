import { registerTelemetryTap, unregisterTelemetryTap } from '../telemetryTap';
import { __setDebugTap } from '../../services/telemetryService';
import { useDebugStore } from '../debugStore';

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

jest.mock('../../services/telemetryService', () => ({
  __setDebugTap: jest.fn(),
}));

describe('telemetryTap', () => {
  beforeEach(() => {
    useDebugStore.setState({ telemetryTail: [], telemetryUnreadCount: 0 });
    jest.clearAllMocks();
  });

  it('registerTelemetryTap installs a function that pushes into debugStore', () => {
    registerTelemetryTap();
    const installed = (__setDebugTap as jest.Mock).mock.calls[0][0];
    expect(typeof installed).toBe('function');

    installed(
      {
        device_id: 'abc',
        event_date: '2026-05-15',
        time_of_day: '12:00:00',
        lat: null,
        lon: null,
      },
      'ok',
    );

    const tail = useDebugStore.getState().telemetryTail;
    expect(tail).toHaveLength(1);
    expect(tail[0].outcome).toBe('ok');
    expect(tail[0].payload.device_id).toBe('abc');
  });

  it('unregisterTelemetryTap clears the slot', () => {
    registerTelemetryTap();
    unregisterTelemetryTap();

    expect(__setDebugTap).toHaveBeenLastCalledWith(undefined);
  });
});

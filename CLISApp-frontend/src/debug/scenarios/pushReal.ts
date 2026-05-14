import { Platform } from 'react-native';
import { useDebugStore } from '../debugStore';
import { pickTemplate } from '../templates';
import { firePushSimulated } from './pushSim';

const TIMEOUT_MS = 3000;

export const firePushReal = async (apiBaseUrl: string): Promise<void> => {
  if (Platform.OS !== 'android') {
    return;
  }

  const store = useDebugStore.getState();
  const template = pickTemplate(store.pushRotationIndex);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let bumpInFinally = true;

  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/debug/fcm-test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: template.title,
        body: template.body,
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      firePushSimulated();
      bumpInFinally = false;
      return;
    }
  } catch {
    firePushSimulated();
    bumpInFinally = false;
  } finally {
    clearTimeout(timer);
    if (bumpInFinally) {
      store.bumpPushRotation();
    }
  }
};

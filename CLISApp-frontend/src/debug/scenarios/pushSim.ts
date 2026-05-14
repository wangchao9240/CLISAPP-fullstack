import { Alert } from 'react-native';
import { useDebugStore } from '../debugStore';
import { pickTemplate } from '../templates';

export const firePushSimulated = (): void => {
  const store = useDebugStore.getState();
  const template = pickTemplate(store.pushRotationIndex);

  Alert.alert(template.title, template.body);
  store.bumpPushRotation();
};

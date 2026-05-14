export interface PushTemplate {
  key: 'heatwave' | 'smoke' | 'uv-extreme';
  title: string;
  body: string;
}

export const PUSH_TEMPLATES: readonly PushTemplate[] = [
  {
    key: 'heatwave',
    title: 'Extreme Heat Warning',
    body:
      'Temperatures forecast to exceed 42 C in Brisbane today. Stay hydrated and avoid outdoor activity 11am-3pm.',
  },
  {
    key: 'smoke',
    title: 'Air Quality Alert',
    body:
      'PM2.5 levels above guideline in your area. Limit outdoor activity if you have respiratory conditions.',
  },
  {
    key: 'uv-extreme',
    title: 'Extreme UV Alert',
    body:
      'UV index forecast at 11+ today. Sunscreen, hat, and shade strongly recommended between 10am and 4pm.',
  },
] as const;

export const pickTemplate = (index: number): PushTemplate =>
  PUSH_TEMPLATES[index % PUSH_TEMPLATES.length];

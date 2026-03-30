export const CATEGORY_BADGE_COLORS: Record<
  string,
  { bg: string; text: string; dot: string }
> = {
  'Very Low': { bg: '#C8E6C9', text: '#1B5E20', dot: '#66BB6A' },
  Low: { bg: '#DCEDC8', text: '#33691E', dot: '#66BB6A' },
  Moderate: { bg: '#FFDBC7', text: '#733600', dot: '#FDD835' },
  High: { bg: '#FFCCBC', text: '#BF360C', dot: '#FF8A65' },
  'Very High': { bg: '#FFCDD2', text: '#B71C1C', dot: '#E57373' },
};

export const DEFAULT_BADGE_COLORS = {
  bg: '#FFDBC7',
  text: '#733600',
  dot: '#BDBDBD',
};

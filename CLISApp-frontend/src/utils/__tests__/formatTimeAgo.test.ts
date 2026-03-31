import { formatTimeAgo } from '../formatTimeAgo';

describe('formatTimeAgo', () => {
  const fixedNow = Date.parse('2026-03-31T12:00:00.000Z');

  beforeEach(() => {
    jest.spyOn(Date, 'now').mockReturnValue(fixedNow);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('returns "Just now" for timestamps less than 60 seconds ago', () => {
    expect(formatTimeAgo(new Date(fixedNow - 59_000).toISOString())).toBe('Just now');
  });

  it('returns "1 minute ago" for timestamps between 60 and 119 seconds ago', () => {
    expect(formatTimeAgo(new Date(fixedNow - 60_000).toISOString())).toBe('1 minute ago');
    expect(formatTimeAgo(new Date(fixedNow - 119_000).toISOString())).toBe('1 minute ago');
  });

  it('returns "5 minutes ago" for timestamps 300 seconds ago', () => {
    expect(formatTimeAgo(new Date(fixedNow - 300_000).toISOString())).toBe('5 minutes ago');
  });

  it('returns "1 hour ago" for timestamps 3600 seconds ago', () => {
    expect(formatTimeAgo(new Date(fixedNow - 3_600_000).toISOString())).toBe('1 hour ago');
  });

  it('returns "2 hours ago" for timestamps 7200 seconds ago', () => {
    expect(formatTimeAgo(new Date(fixedNow - 7_200_000).toISOString())).toBe('2 hours ago');
  });

  it('returns "1 day ago" for timestamps 86400 seconds ago', () => {
    expect(formatTimeAgo(new Date(fixedNow - 86_400_000).toISOString())).toBe('1 day ago');
  });

  it('returns "2 days ago" for timestamps 172800 seconds ago', () => {
    expect(formatTimeAgo(new Date(fixedNow - 172_800_000).toISOString())).toBe('2 days ago');
  });

  it('returns "Unknown" for missing or invalid timestamps', () => {
    expect(formatTimeAgo('')).toBe('Unknown');
    expect(formatTimeAgo(undefined)).toBe('Unknown');
    expect(formatTimeAgo(null)).toBe('Unknown');
    expect(formatTimeAgo('not-a-date')).toBe('Unknown');
  });

  it('returns "Just now" for future timestamps', () => {
    expect(formatTimeAgo(new Date(fixedNow + 60_000).toISOString())).toBe('Just now');
  });
});

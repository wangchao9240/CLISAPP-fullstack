export function formatTimeAgo(isoString?: string | null): string {
  if (!isoString) {
    return 'Unknown';
  }

  const parsed = Date.parse(isoString);

  if (Number.isNaN(parsed)) {
    return 'Unknown';
  }

  const diffSeconds = Math.floor((Date.now() - parsed) / 1000);

  if (diffSeconds < 60) {
    return 'Just now';
  }

  if (diffSeconds < 120) {
    return '1 minute ago';
  }

  if (diffSeconds < 3600) {
    return `${Math.floor(diffSeconds / 60)} minutes ago`;
  }

  if (diffSeconds < 7200) {
    return '1 hour ago';
  }

  if (diffSeconds < 86400) {
    return `${Math.floor(diffSeconds / 3600)} hours ago`;
  }

  if (diffSeconds < 172800) {
    return '1 day ago';
  }

  return `${Math.floor(diffSeconds / 86400)} days ago`;
}

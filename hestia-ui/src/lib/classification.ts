export const CLASSIFICATION_LABELS: Record<number, string> = {
  0: 'Public',
  1: 'Internal',
  2: 'Confidential',
  3: 'Restricted',
  4: 'Secret',
};

export const CLASSIFICATION_OPTIONS = [0, 1, 2, 3, 4] as const;

export function classificationLabel(level: number | null): string {
  if (level === null) return 'No cap';
  return CLASSIFICATION_LABELS[level] ?? `Level ${level}`;
}

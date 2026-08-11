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

// Per-document classification labels, sent as a metadata string override and
// matched against hestia/domain/rag/classification.py's Classification aliases.
// Intentionally NOT derived from CLASSIFICATION_LABELS above: that map is used
// for the numeric tenant "max classification" access cap and has levels 2/3
// swapped relative to the backend Classification enum (RESTRICTED=2, CONFIDENTIAL=3).
export const DOCUMENT_CLASSIFICATION_OPTIONS: { value: string; label: string }[] = [
  { value: 'public',       label: 'Public' },
  { value: 'internal',     label: 'Internal' },
  { value: 'restricted',   label: 'Restricted' },
  { value: 'confidential', label: 'Confidential' },
  { value: 'secret',       label: 'Secret' },
];

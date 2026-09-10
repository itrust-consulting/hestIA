// Numeric levels must match hestia/domain/rag/classification.py's Classification
// enum exactly (PUBLIC=0, INTERNAL=1, RESTRICTED=2, CONFIDENTIAL=3, SECRET=4) --
// this is the value stored as a user's clearance / a collection's max_classification
// and compared server-side, so any drift here silently grants/denies the wrong tier
// (see TRP-018).
export const CLASSIFICATION_LABELS: Record<number, string> = {
  0: 'Public',
  1: 'Internal',
  2: 'Restricted',
  3: 'Confidential',
  4: 'Secret',
};

export const CLASSIFICATION_OPTIONS = [0, 1, 2, 3, 4] as const;

export function classificationLabel(level: number | null): string {
  if (level === null) return 'No cap';
  return CLASSIFICATION_LABELS[level] ?? `Level ${level}`;
}

// Per-document classification labels, sent as a metadata string override and
// matched against hestia/domain/rag/classification.py's Classification aliases.
// Kept as string values rather than the numeric levels above: document tagging
// resolves through label matching, independent of the numeric clearance/cap
// assigned to users and collections.
export const DOCUMENT_CLASSIFICATION_OPTIONS: { value: string; label: string }[] = [
  { value: 'public',       label: 'Public' },
  { value: 'internal',     label: 'Internal' },
  { value: 'restricted',   label: 'Restricted' },
  { value: 'confidential', label: 'Confidential' },
  { value: 'secret',       label: 'Secret' },
];

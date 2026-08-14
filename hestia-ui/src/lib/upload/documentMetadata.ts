// Shared between DocumentUploadModal (initial upload) and DocumentMetadataModal
// (post-upload edit) so the reserved/duplicate-key validation rules for custom
// metadata fields can't drift between the two flows.

export const META_FIELDS: { key: string; label: string }[] = [
  { key: 'title',     label: 'Title' },
  { key: 'author',    label: 'Author' },
  { key: 'publisher', label: 'Publisher' },
  { key: 'version',   label: 'Version' },
  { key: 'year',      label: 'Year' },
];

// Full set of keys the parse endpoint may populate / that get sent as
// metadata overrides on upload.
export const ALL_METADATA_KEYS = [...META_FIELDS.map(({ key }) => key), 'classification', 'lang'];

// Field names a power user's custom metadata field may not use — they're
// already owned by a fixed form field or computed server-side.
export const RESERVED_METADATA_KEYS = [...ALL_METADATA_KEYS, 'source', 'source_uri', 'document_id', 'chunking_strategy'];

export type CustomField = { key: string; value: string };

// Blank-key rows are just in-progress additions, not errors — they're
// ignored on upload rather than blocked.
export function customFieldKeyError(customFields: CustomField[], key: string, index: number): string | null {
  const trimmed = key.trim().toLowerCase();
  if (!trimmed) return null;
  if (RESERVED_METADATA_KEYS.includes(trimmed)) return 'Reserved field name';
  if (customFields.some((f, i) => i !== index && f.key.trim().toLowerCase() === trimmed)) return 'Duplicate field name';
  return null;
}

export function toCustomFieldsRecord(customFields: CustomField[]): Record<string, string> {
  return Object.fromEntries(
    customFields
      .filter((f, i) => f.key.trim() && !customFieldKeyError(customFields, f.key, i))
      .map((f) => [f.key.trim(), f.value])
  );
}

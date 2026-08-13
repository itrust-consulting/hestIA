// Every value here must be a valid PyStemmer/Snowball algorithm name
// (verified against Stemmer.algorithms()), since it's sent straight through
// to Stemmer.Stemmer(lang) — see hestia/domain/rag/services.py. Excludes
// 'porter' and 'dutch_porter': those are alternate stemming algorithms for
// English/Dutch, not distinct languages, and this value also gets stored as
// the document's `lang` metadata.
export const LANGUAGE_OPTIONS: { value: string; label: string }[] = [
  { value: 'arabic',      label: 'Arabic' },
  { value: 'armenian',    label: 'Armenian' },
  { value: 'basque',      label: 'Basque' },
  { value: 'catalan',     label: 'Catalan' },
  { value: 'danish',      label: 'Danish' },
  { value: 'dutch',       label: 'Dutch' },
  { value: 'english',     label: 'English' },
  { value: 'esperanto',   label: 'Esperanto' },
  { value: 'estonian',    label: 'Estonian' },
  { value: 'finnish',     label: 'Finnish' },
  { value: 'french',      label: 'French' },
  { value: 'german',      label: 'German' },
  { value: 'greek',       label: 'Greek' },
  { value: 'hindi',       label: 'Hindi' },
  { value: 'hungarian',   label: 'Hungarian' },
  { value: 'indonesian',  label: 'Indonesian' },
  { value: 'irish',       label: 'Irish' },
  { value: 'italian',     label: 'Italian' },
  { value: 'lithuanian',  label: 'Lithuanian' },
  { value: 'nepali',      label: 'Nepali' },
  { value: 'norwegian',   label: 'Norwegian' },
  { value: 'portuguese',  label: 'Portuguese' },
  { value: 'romanian',    label: 'Romanian' },
  { value: 'russian',     label: 'Russian' },
  { value: 'serbian',     label: 'Serbian' },
  { value: 'spanish',     label: 'Spanish' },
  { value: 'swedish',     label: 'Swedish' },
  { value: 'tamil',       label: 'Tamil' },
  { value: 'turkish',     label: 'Turkish' },
  { value: 'yiddish',     label: 'Yiddish' },
];

// Best-effort mapping from a parsed document's raw language string to one of
// the values above. Returns '' when unsure — Language is a required field in
// the upload wizard, so an uncertain guess must fall back to an explicit
// user choice rather than silently picking the wrong stemmer.
export function guessLanguage(raw: string | undefined | null): string {
  if (!raw) return '';
  const cleaned = raw.trim().toLowerCase();
  const aliasMap: Record<string, string> = {
    english: 'english', en: 'english', eng: 'english',
    french: 'french', fr: 'french', fra: 'french', francais: 'french',
    german: 'german', de: 'german', ger: 'german', deutsch: 'german',
  };
  return aliasMap[cleaned] ?? '';
}

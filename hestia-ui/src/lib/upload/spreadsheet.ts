// Sheet-splitting for markdown produced from spreadsheet uploads (xlsx/xlsm) --
// each sheet becomes its own "## Sheet Name" section in the parsed markdown.
// Extracted out of DocumentUploadModal.svelte, which previously defined these
// alongside its drag-and-drop/upload-orchestration code; both are pure
// functions with no dependency on component state.

export function extractSheets(md: string): string[] {
  const names: string[] = [];
  for (const line of md.split('\n')) {
    const m = /^## (.+)$/.exec(line.trim());
    if (m) names.push(m[1].trim());
  }
  return names;
}

export function splitToSheets(md: string, sheets: string[]): Record<string, string> {
  const result: Record<string, string> = {};
  const sections = md.split(/\n(?=## )/);
  for (const section of sections) {
    const name = /^## (.+)/.exec(section.trimStart())?.[1]?.trim();
    if (name && sheets.includes(name)) result[name] = section.trimStart();
  }
  return result;
}

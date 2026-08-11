export type SelectedFile = { file: File; relPath: string };

/** Extensions accepted for ingestion. Single source of truth — keep the
 *  <input accept=...> attribute in DocumentUploadModal.svelte in sync with this. */
export const ACCEPTED_EXTS = [
  '.docx', '.pdf', '.xlsx', '.xlsm', '.json', '.csv', '.txt', '.md', '.markdown', '.pptx',
];

/** Directory (base)names to skip entirely, even if a file inside matches ACCEPTED_EXTS. */
const IGNORED_DIR_NAMES = new Set(['node_modules', '__pycache__', '.venv', 'dist', 'build']);

function isAccepted(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPTED_EXTS.some(ext => lower.endsWith(ext));
}

function isIgnoredDirName(name: string): boolean {
  return name.startsWith('.') || IGNORED_DIR_NAMES.has(name);
}

/** Does any path segment (excluding the filename itself) match an ignored directory? */
function hasIgnoredSegment(relPath: string): boolean {
  const segments = relPath.split('/');
  segments.pop(); // drop filename
  return segments.some(isIgnoredDirName);
}

/**
 * Build filtered SelectedFile[] from a `webkitdirectory` <input>'s FileList.
 * file.webkitRelativePath looks like "TopFolder/sub/file.md".
 */
export function fromFileList(fileList: FileList): SelectedFile[] {
  const out: SelectedFile[] = [];
  for (const file of Array.from(fileList)) {
    const relPath = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    if (!isAccepted(file.name)) continue;
    if (hasIgnoredSegment(relPath)) continue;
    out.push({ file, relPath });
  }
  return out;
}

/**
 * Recursively walk a DataTransferItemList (from a drop event) into filtered SelectedFile[].
 * Returns null if the browser doesn't support webkitGetAsEntry — caller should then fall
 * back to flat e.dataTransfer.files handling.
 */
export async function fromDataTransferItems(items: DataTransferItemList): Promise<SelectedFile[] | null> {
  const roots: FileSystemEntry[] = [];
  for (const item of Array.from(items)) {
    const entry = (item as DataTransferItem & { webkitGetAsEntry?: () => FileSystemEntry | null }).webkitGetAsEntry?.();
    if (!entry) return null; // unsupported — signal fallback
    roots.push(entry);
  }

  const out: SelectedFile[] = [];

  async function walk(entry: FileSystemEntry): Promise<void> {
    const relPath = entry.fullPath.replace(/^\/+/, '');

    if (entry.isFile) {
      if (!isAccepted(entry.name)) return;
      if (hasIgnoredSegment(relPath)) return;
      const file = await new Promise<File>((resolve, reject) =>
        (entry as FileSystemFileEntry).file(resolve, reject)
      );
      out.push({ file, relPath });
      return;
    }

    if (entry.isDirectory) {
      if (isIgnoredDirName(entry.name)) return;
      const reader = (entry as FileSystemDirectoryEntry).createReader();
      // readEntries() must be called repeatedly until it returns [] — a single call
      // is not guaranteed to return all entries (esp. large directories in Chrome).
      let batch: FileSystemEntry[];
      do {
        batch = await new Promise<FileSystemEntry[]>((resolve, reject) =>
          reader.readEntries(resolve, reject)
        );
        for (const child of batch) await walk(child);
      } while (batch.length > 0);
    }
  }

  for (const root of roots) await walk(root);
  return out;
}

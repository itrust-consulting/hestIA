import { describe, expect, it } from 'vitest';

import { fromFileList } from '$lib/upload/folderSelect';

function fileWithRelPath(relPath: string): File {
	const name = relPath.split('/').pop()!;
	const file = new File(['content'], name, { type: 'text/plain' });
	Object.defineProperty(file, 'webkitRelativePath', { value: relPath });
	return file;
}

function fakeFileList(files: File[]): FileList {
	return files as unknown as FileList;
}

describe('folderSelect / fromFileList', () => {
	it('keeps files with an accepted extension', () => {
		const result = fromFileList(fakeFileList([fileWithRelPath('repo/docs/guide.md')]));
		expect(result).toHaveLength(1);
		expect(result[0].relPath).toBe('repo/docs/guide.md');
	});

	it('drops files with an unsupported extension', () => {
		const result = fromFileList(fakeFileList([fileWithRelPath('repo/logo.png')]));
		expect(result).toHaveLength(0);
	});

	it('skips files inside ignored directories even with an accepted extension', () => {
		const result = fromFileList(
			fakeFileList([
				fileWithRelPath('repo/node_modules/pkg/readme.md'),
				fileWithRelPath('repo/.git/HEAD.md'),
				fileWithRelPath('repo/__pycache__/notes.txt'),
				fileWithRelPath('repo/docs/guide.md'),
			])
		);
		expect(result.map(r => r.relPath)).toEqual(['repo/docs/guide.md']);
	});

	it('falls back to file.name when webkitRelativePath is absent', () => {
		const file = new File(['x'], 'loose.txt', { type: 'text/plain' });
		const result = fromFileList(fakeFileList([file]));
		expect(result).toHaveLength(1);
		expect(result[0].relPath).toBe('loose.txt');
	});
});

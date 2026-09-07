import { describe, it, expect } from 'vitest';
import { extractSheets, splitToSheets } from './spreadsheet';

describe('extractSheets', () => {
  it('extracts sheet names from ## headings', () => {
    const md = '## Sheet1\ncontent\n\n## Sheet2\nmore content';
    expect(extractSheets(md)).toEqual(['Sheet1', 'Sheet2']);
  });

  it('returns an empty array when there are no sheet headings', () => {
    expect(extractSheets('just some text\nno headings here')).toEqual([]);
  });

  it('trims whitespace around the sheet name', () => {
    expect(extractSheets('##   Padded Name   \n')).toEqual(['Padded Name']);
  });

  it('ignores headings that are not at the start of a trimmed line', () => {
    expect(extractSheets('text ## Not A Heading')).toEqual([]);
  });
});

describe('splitToSheets', () => {
  it('splits markdown into one entry per named sheet', () => {
    const md = '## Sheet1\nrow a\nrow b\n\n## Sheet2\nrow c';
    const result = splitToSheets(md, ['Sheet1', 'Sheet2']);
    expect(Object.keys(result)).toEqual(['Sheet1', 'Sheet2']);
    expect(result['Sheet1']).toContain('row a');
    expect(result['Sheet2']).toContain('row c');
  });

  it('only includes sheets present in the requested list', () => {
    const md = '## Keep\ncontent\n\n## Drop\nother content';
    const result = splitToSheets(md, ['Keep']);
    expect(Object.keys(result)).toEqual(['Keep']);
  });

  it('returns an empty object when no section matches', () => {
    const md = '## Unrelated\ncontent';
    expect(splitToSheets(md, ['Nonexistent'])).toEqual({});
  });
});

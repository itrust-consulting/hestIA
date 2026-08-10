import { listSections, getSection } from '$lib/server/help/sections';

export async function load({ url }) {
  const section = url.searchParams.get('section') ?? 'getting-started';
  const sections = await listSections();

  let content = '';
  try {
    content = (await getSection(section)) ?? '';
  } catch {
    content = '';
  }

  return { section, sections, content };
}

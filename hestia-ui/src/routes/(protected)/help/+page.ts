export async function load({ url, fetch }) {
  const section = url.searchParams.get('section') ?? 'getting-started';

  const [sectionsRes, contentRes] = await Promise.all([
    fetch('/api/help'),
    fetch(`/api/help/${section}`)
  ]);

  const { sections } = sectionsRes.ok ? await sectionsRes.json() : { sections: [] };
  const content = contentRes.ok ? await contentRes.text() : '';

  return { section, sections, content };
}

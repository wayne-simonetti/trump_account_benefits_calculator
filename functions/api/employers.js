export async function onRequestGet({ env }) {
  const { results } = await env.DB.prepare(
    `SELECT id, name, grant_amount, condition_type, group_label, note, contribution_type, source_url
     FROM employers ORDER BY sort_order, name`
  ).all();

  const employers = results.map(r => {
    const amt = r.grant_amount ?? 0;
    const entry = {
      group: r.group_label,
      label: r.name,
      value: `${r.id}|${amt}|${r.condition_type}|${r.contribution_type}`,
    };
    if (r.note) entry.note = r.note;
    if (r.source_url) entry.source_url = r.source_url;
    return entry;
  });

  return Response.json(employers, {
    headers: { 'Cache-Control': 'public, max-age=3600' },
  });
}

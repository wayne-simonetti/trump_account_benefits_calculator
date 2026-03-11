export async function onRequestGet({ request, env }) {
  const zip = new URL(request.url).searchParams.get('zip');
  if (!zip || !/^\d{5}$/.test(zip))
    return Response.json({ error: 'Invalid ZIP' }, { status: 400 });

  const row = await env.DB.prepare(
    'SELECT median_income, year FROM zip_income WHERE zip = ?'
  ).bind(zip).first();

  return Response.json(
    row
      ? { zip, median_income: row.median_income, vintage_year: row.year }
      : { zip, median_income: null },
    { headers: { 'Cache-Control': 'public, max-age=86400' } }
  );
}

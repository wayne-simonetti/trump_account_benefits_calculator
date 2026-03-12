export async function onRequestGet({ env }) {
  const { results } = await env.DB.prepare(
    `SELECT id, state_code, grantor_name, donor_line, grant_amount, amount_display,
            req_no_seed, req_has_seed, req_age_max, req_born_year,
            req_zip_income, income_cap, req_zip_set,
            req_county_checkbox, county_checkbox_label, county_checkbox_label2,
            note, source_url, sort_order
     FROM state_grants ORDER BY sort_order, grantor_name`
  ).all();

  return Response.json(results, {
    headers: { 'Cache-Control': 'public, max-age=3600' },
  });
}

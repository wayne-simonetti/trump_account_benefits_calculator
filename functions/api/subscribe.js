// POST /api/subscribe  — launch-notification signup.
//
// Flow: verify Cloudflare Turnstile -> validate email -> INSERT OR IGNORE into
// D1 `subscribers` (you own the data) -> best-effort forward to Kit.
//
// Required Pages env (set in Cloudflare dashboard as Secrets, never in repo):
//   TURNSTILE_SECRET  - Turnstile secret key
//   KIT_API_SECRET    - Kit (ConvertKit) API secret
//   KIT_FORM_ID       - Kit form id (plain var is fine)
//   IP_SALT           - random string; salts the stored IP hash
//
// Public-repo note: this file is world-readable by design. Security rests on
// the Turnstile secret + server-side validation, not on code being hidden.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });

async function sha256(str) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function verifyTurnstile(token, ip, secret) {
  if (!secret || !token) return false;
  const body = new FormData();
  body.append('secret', secret);
  body.append('response', token);
  if (ip) body.append('remoteip', ip);
  try {
    const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      body,
    });
    const data = await r.json();
    return data.success === true;
  } catch {
    return false; // fail closed
  }
}

export async function onRequestPost({ request, env }) {
  let email, token;
  try {
    const ct = request.headers.get('Content-Type') || '';
    if (ct.includes('application/json')) {
      const b = await request.json();
      email = b.email;
      token = b.turnstileToken;
    } else {
      const f = await request.formData();
      email = f.get('email');
      token = f.get('cf-turnstile-response');
    }
  } catch {
    return json({ ok: false, error: 'bad_request' }, 400);
  }

  email = (email || '').toString().trim().toLowerCase();
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return json({ ok: false, error: 'invalid_email' }, 400);
  }

  const ip = request.headers.get('CF-Connecting-IP') || '';
  const ok = await verifyTurnstile(token, ip, env.TURNSTILE_SECRET);
  if (!ok) return json({ ok: false, error: 'verification_failed' }, 403);

  const ipHash = ip ? await sha256(ip + '|' + (env.IP_SALT || '')) : null;

  // Defense-in-depth burst guard (Turnstile is the primary bot control;
  // a Cloudflare WAF rate-limit rule on this route is the recommended layer).
  try {
    const recent = await env.DB.prepare(
      `SELECT COUNT(*) AS n FROM subscribers
       WHERE ip_hash = ? AND created_at > datetime('now','-1 minute')`
    ).bind(ipHash).first();
    if (recent && recent.n >= 5) {
      return json({ ok: false, error: 'rate_limited' }, 429);
    }
  } catch {
    // table may not exist yet in a fresh env; don't hard-fail the user
  }

  // Own the data first. Dedupe on UNIQUE(email).
  try {
    await env.DB.prepare(
      `INSERT OR IGNORE INTO subscribers (email, created_at, source, ip_hash)
       VALUES (?, datetime('now'), 'calculator', ?)`
    ).bind(email, ipHash).run();
  } catch {
    return json({ ok: false, error: 'storage_error' }, 500);
  }

  // Best-effort forward to Kit. Failure here is non-fatal: the address is
  // already in D1 with kit_synced=0 and can be resynced later.
  if (env.KIT_API_SECRET && env.KIT_FORM_ID) {
    try {
      const kr = await fetch(
        `https://api.kit.com/v3/forms/${env.KIT_FORM_ID}/subscribe`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_secret: env.KIT_API_SECRET, email }),
        }
      );
      if (kr.ok) {
        await env.DB.prepare(
          `UPDATE subscribers SET kit_synced = 1 WHERE email = ?`
        ).bind(email).run();
      }
    } catch {
      // swallow — resync path covers this
    }
  }

  return json({ ok: true });
}

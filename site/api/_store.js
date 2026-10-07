// Společné pro ask.js a hit.js: kontrola původu požadavku a anonymní záznam do Upstash Redis.
const ALLOWED_HOSTS = ["lukas-rag.vercel.app", "localhost", "127.0.0.1"];

function allowedOrigin(req) {
  const o = req.headers.origin || req.headers.referer || "";
  try { const h = new URL(o).hostname; return ALLOWED_HOSTS.includes(h) || h.endsWith("-zenkiyeai-5446.vercel.app"); } catch { return false; }
}

// ---------- záznam otázek (anonymně, bez IP) ----------
// Upstash Redis přes REST; bez proměnných prostředí se nic neukládá a vše funguje dál.
async function store(cmds) {
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const tok = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !tok) return;
  try {
    await Promise.race([
      fetch(url + "/pipeline", { method: "POST", headers: { Authorization: `Bearer ${tok}` }, body: JSON.stringify(cmds) }),
      new Promise(res => setTimeout(res, 1500)),
    ]);
  } catch {}
}

module.exports = { store, allowedOrigin };

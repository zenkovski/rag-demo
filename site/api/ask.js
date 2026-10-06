// Živá otázka: stejný postup jako tools/rag.py (přepis -> e5-large + BM25 -> RRF -> odpověď s citacemi).
// Klíč je jen v proměnné prostředí OPENROUTER_API_KEY na Vercelu, nikdy v kódu ani na stránce.
// Ochrana proti spamu: 10 otázek na IP za den, malý výpočetní test (proof of work), délka otázky,
// kontrola původu požadavku. Nejtvrdší pojistka je limit 0,50 $ přímo na klíči v OpenRouteru.
const crypto = require("crypto");
const IDX = require("./_index.json");

const PER_IP_PER_DAY = 10;
const GLOBAL_PER_DAY = 400;        // strop na jednu instanci funkce
const POW_ZEROS = "0000";          // sha256 musí začínat 4 nulami (~65 000 pokusů v prohlížeči)
const MAX_LEN = 300;
const ALLOWED_HOSTS = ["lukas-rag.vercel.app", "localhost", "127.0.0.1"];

// ---------- data ----------
const N = IDX.chunks.length;
// vektory jsou int8 + 1 měřítko na úsek (4× menší soubor); převod dá přesně stejná čísla jako rag.index() v Pythonu
const Q8 = new Int8Array(Buffer.from(IDX.vectors, "base64").buffer.slice(0));
const SCALE = new Float32Array(Buffer.from(IDX.scales, "base64").buffer.slice(0));
const VEC = new Float32Array(Q8.length);
for (let i = 0; i < Q8.length; i++) VEC[i] = Q8[i] * SCALE[Math.floor(i / IDX.dim)];
for (let i = 0; i < IDX.chunks.length; i++) {            // znovu na délku 1 (jako rag.dequantize)
  const v = VEC.subarray(i * IDX.dim, (i + 1) * IDX.dim); let n = 0;
  for (let j = 0; j < v.length; j++) n += v[j] * v[j];
  n = Math.sqrt(n); for (let j = 0; j < v.length; j++) v[j] = v[j] / n;
}
const vecOf = i => VEC.subarray(i * IDX.dim, (i + 1) * IDX.dim);

// ---------- BM25 (shodné s tools/rag.py) ----------
const strip = s => s.normalize("NFD").replace(/\p{Mn}/gu, "");
const STOP = new Set(IDX.stop.map(s => strip(s.toLowerCase())));
function tokens(text) {
  const words = strip(text.toLowerCase()).match(/[a-z0-9]+/g) || [];
  return words.filter(w => w.length > 2 && !STOP.has(w)).map(w => w.slice(0, 5));
}
const DOCS = IDX.chunks.map(c => { const m = new Map(); for (const w of tokens(`${c.title} ${c.text}`)) m.set(w, (m.get(w) || 0) + 1); return m; });
const LENS = DOCS.map(d => [...d.values()].reduce((a, b) => a + b, 0));
const AVG = LENS.reduce((a, b) => a + b, 0) / N;
const DF = new Map(); for (const d of DOCS) for (const w of d.keys()) DF.set(w, (DF.get(w) || 0) + 1);
function bm25(text, k1 = 1.5, b = 0.75) {
  const s = new Float64Array(N);
  for (const w of new Set(tokens(text))) {
    const df = DF.get(w); if (!df) continue;
    const idf = Math.log(1 + (N - df + 0.5) / (df + 0.5));
    for (let i = 0; i < N; i++) { const tf = DOCS[i].get(w) || 0; s[i] += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * LENS[i] / AVG)); }
  }
  return s;
}

// ---------- hledání ----------
function cosineAll(q) { const s = new Float64Array(N); for (let i = 0; i < N; i++) { const v = vecOf(i); let d = 0; for (let j = 0; j < v.length; j++) d += v[j] * q[j]; s[i] = d; } return s; }
function top(scores, n = 50) {   // stabilní řazení, nulová skóre se nepočítají (jako np.argsort kind="stable")
  return [...scores.keys()].sort((a, b) => scores[b] - scores[a] || a - b).slice(0, n).filter(i => scores[i] > 0);
}
function rrf(rankings, k = 60) {
  const sc = new Map();
  for (const r of rankings) r.forEach((i, rank) => sc.set(i, (sc.get(i) || 0) + 1 / (k + rank + 1)));
  return [...sc.entries()].sort((a, b) => b[1] - a[1]);
}
function search(qVec, rwVec, rewritten) {
  const d = cosineAll(qVec);
  const steps = { dense_q: top(d), dense_rw: top(cosineAll(rwVec)), bm25: top(bm25(rewritten)) };
  const fused = rrf([steps.dense_q, steps.dense_rw, steps.bm25]);
  const trace = Object.fromEntries(Object.entries(steps).map(([k, v]) => [k, v.slice(0, 20)]));
  trace.fused = fused.slice(0, IDX.n_cand).map(([i, s]) => [i, Math.round(s * 1e5) / 1e5]);
  return { d, fused, trace };
}
// v3: LLM vybere z 20 kandidátů ty, které k odpovědi patří (shodné s rag.rerank / rag.parse_pick)
function rerankPrompt(q, rewritten, cands) {
  return `Otázka: ${q}\nV jazyce zákona: ${rewritten}\n\nÚseky:\n` + cands.map((i, n) => {
    const c = IDX.chunks[i]; return `[${n + 1}] ${c.id} (${c.title}): ${[...c.text].slice(0, 400).join("")}`; }).join("\n");
}
function parsePick(text, n) {
  const out = [];
  for (const m of text.match(/\d+/g) || []) { const x = +m; if (x >= 1 && x <= n && !out.includes(x - 1)) out.push(x - 1); }
  return out.slice(0, IDX.top_k);
}
// za vybraný odstavec 2, 3… přidá odstavec 1 téhož § (i mimo kandidáty), shodné s rag.with_odst1
function withOdst1(picked, cands) {
  const out = [];
  for (const i of picked) {
    const j = IDX.chunks[i].o1;
    for (const x of [i, j]) if (x !== undefined && !out.includes(x) && (x === i || !picked.includes(x))) out.push(x);
  }
  return out.slice(0, IDX.top_k);
}
function finalHits(d, fused, picked) {
  const order = [...picked, ...fused.map(([i]) => i).filter(i => !picked.includes(i))];
  return order.slice(0, IDX.top_k).map(i => [i, Math.round(d[i] * 1000) / 1000]);
}

// ---------- OpenRouter ----------
async function call(path, body) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const r = await fetch("https://openrouter.ai/api/v1/" + path, {
      method: "POST", body: JSON.stringify(body),
      headers: { "Authorization": `Bearer ${process.env.OPENROUTER_API_KEY}`, "Content-Type": "application/json",
                 "HTTP-Referer": "https://lukas-rag.vercel.app", "X-Title": "rag-demo" } });
    const data = await r.json().catch(() => ({}));
    if (r.ok && !data.error) return data;
    if (r.status === 402 || (data.error && /credit|limit/i.test(data.error.message || ""))) throw Object.assign(new Error("budget"), { budget: true });
    if (r.status !== 429 && r.status < 500 && !data.error) throw new Error(`OpenRouter ${r.status}`);
    await new Promise(res => setTimeout(res, 1500 * (attempt + 1)));
  }
  throw new Error("OpenRouter nedostupný");
}
// reasoning vypnutý jako v rag.py (v3): bez skrytého přemýšlení je odpověď ~10× rychlejší a levnější
const chat = async (system, user) => (await call("chat/completions", { model: IDX.llm, temperature: 0, reasoning: { enabled: false },
  messages: [{ role: "system", content: system }, { role: "user", content: user }] })).choices[0].message.content.trim();
async function embed(texts) {
  const data = await call("embeddings", { model: IDX.emb_model, input: texts });
  return data.data.map(d => { const v = Float64Array.from(d.embedding); const n = Math.hypot(...v); return v.map(x => x / n); });
}

// ---------- ochrana ----------
const ipLog = new Map(), seen = new Set();
let day = "", globalCount = 0;
function clientIp(req) { return String(req.headers["x-real-ip"] || (req.headers["x-forwarded-for"] || "").split(",")[0] || "?").trim(); }
function allowedOrigin(req) {
  const o = req.headers.origin || req.headers.referer || "";
  try { const h = new URL(o).hostname; return ALLOWED_HOSTS.includes(h) || h.endsWith("-zenkiyeai-5446.vercel.app"); } catch { return false; }
}

module.exports = async (req, res) => {
  const send = (code, obj) => { res.statusCode = code; res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.setHeader("Cache-Control", "no-store"); res.end(JSON.stringify(obj)); };
  if (req.method !== "POST") return send(405, { error: "Jen POST." });
  if (!allowedOrigin(req) || req.headers["x-rag-client"] !== "web") return send(403, { error: "Požadavek nepřišel ze stránky." });

  const today = new Date().toISOString().slice(0, 10);
  if (today !== day) { day = today; globalCount = 0; ipLog.clear(); seen.clear(); }
  const ip = clientIp(req), used = ipLog.get(ip) || 0;
  if (used >= PER_IP_PER_DAY) return send(429, { error: `Dnešní limit ${PER_IP_PER_DAY} otázek je vyčerpaný. Zkus to zítra, nebo si vyber z předpočítaných otázek.`, remaining: 0 });
  if (globalCount >= GLOBAL_PER_DAY) return send(429, { error: "Dnešní limit pro celý web je vyčerpaný. Zkus to zítra." });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const q = String((body && body.q) || "").replace(/\s+/g, " ").trim();
  const ts = Number(body && body.ts), nonce = String((body && body.nonce) || "");
  if (body && body.website) return send(400, { error: "Neplatný požadavek." });          // past na roboty (skryté pole)
  if (q.length < 8 || q.length > MAX_LEN) return send(400, { error: `Otázka musí mít 8 až ${MAX_LEN} znaků.` });
  if (!ts || Math.abs(Date.now() - ts) > 10 * 60 * 1000) return send(400, { error: "Ověření vypršelo, zkus to znovu." });
  const h = crypto.createHash("sha256").update(`${ts}:${nonce}:${q}`).digest("hex");
  if (!h.startsWith(POW_ZEROS) || seen.has(h)) return send(400, { error: "Ověření se nepovedlo, zkus to znovu." });
  seen.add(h);

  ipLog.set(ip, used + 1); globalCount++;
  try {
    let rewritten = await chat(IDX.rewrite, q);
    rewritten = rewritten.replace(/^"+|"+$/g, "").split(/\r?\n/)[0].trim() || q;
    const [qVec, rwVec] = await embed([`query: ${q}`, `query: ${rewritten}`]);
    const { d, fused, trace } = search(qVec, rwVec, rewritten);
    const cands = fused.slice(0, IDX.n_cand).map(([i]) => i);
    const picked = withOdst1(parsePick(await chat(IDX.rerank, rerankPrompt(q, rewritten, cands)), cands.length).map(j => cands[j]), cands);
    trace.rerank = picked;
    const hits = finalHits(d, fused, picked);
    const ctx = hits.map(([i], n) => `[${n + 1}] ${IDX.chunks[i].id} (${IDX.chunks[i].title}${IDX.chunks[i].note || ""}): ${IDX.chunks[i].text}`).join("\n\n");
    let answer = await chat(IDX.system, `Úseky zákona:\n\n${ctx}\n\nOtázka: ${q}`);
    answer = answer.replace(/【(\d+)】/g, "[$1]");
    return send(200, { q, rewritten, hits, trace, answer, remaining: PER_IP_PER_DAY - used - 1 });
  } catch (e) {
    ipLog.set(ip, used);                       // nepovedené volání se nepočítá
    if (e.budget) return send(503, { error: "Rozpočet na živé otázky je vyčerpaný. Předpočítané otázky fungují dál." });
    return send(502, { error: "Model teď neodpovídá, zkus to za chvíli." });
  }
};
module.exports.config = { maxDuration: 60 };
module.exports.core = { tokens, bm25, top, rrf, search, rerankPrompt, parsePick, withOdst1, finalHits, N };

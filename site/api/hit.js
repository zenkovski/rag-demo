// Klik na připravenou otázku (bez volání AI): jen se přičte počítadlo, ať je vidět, co lidi zajímá. Anonymně, bez IP.
const { store, allowedOrigin } = require("./_store.js");
const PRESETS = new Set(require("./_presets.json"));   // tools/make_presets.py; jen otázky z tohoto seznamu se počítají

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST" || !allowedOrigin(req)) { res.statusCode = 403; return res.end(); }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const q = String((body && body.q) || "").slice(0, 200).trim();
  const src = ["preset", "quick", "sim"].includes(body && body.src) ? body.src : "preset";
  if (q && PRESETS.has(q)) await store([["HINCRBY", "rag:preset", q, 1], ["HINCRBY", "rag:src", src, 1]]);
  res.statusCode = 204; res.end();
};

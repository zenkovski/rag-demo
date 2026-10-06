// Pomocník pro tests/test_rag.py: spustí stejné funkce z webové verze (site/api/ask.js) a vrátí výsledky jako JSON.
// Python je pak porovná se svými, takže web a měření prokazatelně hledají stejně.
const core = require("../site/api/ask.js").core;
const cases = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = {
  tokens: cases.texts.map(t => core.tokens(t)),
  bm25: cases.texts.map(t => core.top(core.bm25(t), 10)),
  rrf: core.rrf(cases.rankings).map(([i]) => i),
  pick: core.parsePick(cases.pick, 20),
  odst1: core.withOdst1(cases.picked, []),
  refs: core.withRefs(cases.hits),
};
process.stdout.write(JSON.stringify(out));

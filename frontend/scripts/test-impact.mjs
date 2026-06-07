import assert from "node:assert/strict";
import { join } from "node:path";
import { loadTsModule } from "./load-ts-module.mjs";

const {
  getImpactDataSourceLabel,
  getImpactDataSourceTone,
  getImpactFormulaRows,
  getImpactPipelineRows,
} = loadTsModule(join(process.cwd(), "src", "utils", "impact.ts"));

const metrics = {
  ai_calls_avoided_estimated: 10,
  cache_reused: false,
  collected_articles: 133,
  data_source: "pipeline_run",
  date: "2026-06-06",
  duplicate_articles: 9,
  duplicate_articles_estimated: 10,
  estimated_data_saved_mb: 88,
  estimated_minutes_saved: 55,
  estimated_pages_avoided: 110,
  has_data: true,
  is_fallback: false,
  methodology: {
    mb_per_page: 0.8,
    minutes_per_article: 0.5,
    note: "Estimaciones orientativas.",
  },
  pipeline: [],
  quality_dropped_articles: 1,
  ranked_articles: 123,
  reduction_rate: 0.827,
  requested_date: "2026-06-06",
  summaries: 23,
  summary_candidates: 24,
  unique_articles: 123,
  usable_articles: 132,
};

assert.equal(getImpactDataSourceLabel("pipeline_run"), "Fuente de datos: corrida real del pipeline.");
assert.equal(
  getImpactDataSourceLabel("derived"),
  "Fuente de datos: estimacion derivada de articulos y briefs guardados.",
);
assert.equal(getImpactDataSourceLabel("empty"), "Sin datos suficientes para calcular impacto.");
assert.equal(getImpactDataSourceTone("pipeline_run"), "strong");
assert.equal(getImpactDataSourceTone("derived"), "muted");
assert.equal(getImpactDataSourceTone("empty"), "empty");

assert.deepEqual(JSON.parse(JSON.stringify(getImpactPipelineRows(metrics))), [
  { label: "Recolectadas", value: 133 },
  { label: "Utiles", value: 132 },
  { label: "Unicas", value: 123 },
  { label: "Candidatas", value: 24 },
  { label: "Briefs", value: 23 },
]);

const formulaRows = getImpactFormulaRows(metrics);
assert.equal(formulaRows[0].value, "133 - 23 = 110");
assert.equal(formulaRows[1].value, "1 - 23 / 133");
assert.equal(formulaRows[2].value, "110 * 0.5 = 55");
assert.equal(formulaRows[3].value, "110 * 0.8 = 88 MB");

console.log("impact tests passed");

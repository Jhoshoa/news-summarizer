import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import vm from "node:vm";
import ts from "typescript";

const sourcePath = join(process.cwd(), "src", "utils", "newsRoute.ts");
const source = readFileSync(sourcePath, "utf8");
const transpiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;

const module = { exports: {} };
vm.runInNewContext(transpiled, {
  URLSearchParams,
  Date,
  Number,
  exports: module.exports,
  module,
});

const {
  buildNewsHref,
  getCategory,
  getCurrentPage,
  getDateValidationMessage,
  getSelectedDate,
  isValidDateValue,
} = module.exports;

assert.equal(getCurrentPage("?page=3"), 3);
assert.equal(getCurrentPage("?page=0"), 1);
assert.equal(getCurrentPage("?page=-1"), 1);
assert.equal(getCurrentPage("?page=abc"), 1);
assert.equal(getCategory("?category=politica"), "politica");
assert.equal(getCategory("?category="), undefined);
assert.equal(isValidDateValue("2026-05-28"), true);
assert.equal(isValidDateValue("2026-02-31"), false);
assert.equal(getSelectedDate("?date=2026-05-28", "2026-05-29"), "2026-05-28");
assert.equal(getSelectedDate("?date=2026-05-30", "2026-05-29"), "2026-05-29");
assert.equal(getSelectedDate("?date=bad", "2026-05-29"), "2026-05-29");
assert.match(
  getDateValidationMessage("?date=2026-05-30", "2026-05-29", "2026-05-29"),
  /futura/,
);
assert.equal(buildNewsHref(2, "2026-05-28", "politica"), "/news?page=2&date=2026-05-28&category=politica");

console.log("newsRoute tests passed");

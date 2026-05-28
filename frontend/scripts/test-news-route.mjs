import assert from "node:assert/strict";
import { join } from "node:path";
import { loadTsModule } from "./load-ts-module.mjs";

const sourcePath = join(process.cwd(), "src", "utils", "newsRoute.ts");
const {
  buildNewsHref,
  getCategory,
  getCurrentPage,
  getDateValidationMessage,
  getSelectedDate,
  isValidDateValue,
} = loadTsModule(sourcePath);

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

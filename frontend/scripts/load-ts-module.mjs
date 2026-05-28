import { readFileSync } from "node:fs";
import vm from "node:vm";
import ts from "typescript";

export const loadTsModule = (sourcePath) => {
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

  return module.exports;
};

import assert from "node:assert/strict";
import { join } from "node:path";
import { loadTsModule } from "./load-ts-module.mjs";

const sourcePath = join(process.cwd(), "src", "utils", "summaryText.ts");
const { buildContextualSummary, cleanGeneratedText } = loadTsModule(sourcePath);

assert.equal(cleanGeneratedText("1. 2) Resumen corto"), "Resumen corto");

assert.equal(
  buildContextualSummary(
    "Se puede realizar Control de Vivencia del Senasir desde casa",
    "El tramite obligatorio de tres meses ya se puede efectuar mediante la aplicacion movil de la Gestora. Esta dirigido a rentistas y derechohabientes.",
  ),
  "Se puede realizar Control de Vivencia del Senasir desde casa. El tramite obligatorio de tres meses ya se puede efectuar mediante la aplicacion movil de la Gestora.",
);

assert.equal(
  buildContextualSummary(
    "El Servicio Nacional de Reparto habilito el control digital para rentistas y derechohabientes, con el fin de mantener activo el beneficio y evitar traslados presenciales.",
    "Contexto adicional que no deberia agregarse.",
  ),
  "El Servicio Nacional de Reparto habilito el control digital para rentistas y derechohabientes, con el fin de mantener activo el beneficio y evitar traslados presenciales.",
);

console.log("summaryText tests passed");

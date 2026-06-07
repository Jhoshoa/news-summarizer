import assert from "node:assert/strict";
import { join } from "node:path";
import { loadTsModule } from "./load-ts-module.mjs";

const { getNavigationState } = loadTsModule(
  join(process.cwd(), "src", "utils", "navigation.ts"),
);

const assertNavigationState = (actual, expected) => {
  assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected);
};

assertNavigationState(getNavigationState("/"), {
  activePath: "/",
  backFallback: "/",
  breadcrumbs: [{ href: "/", label: "Inicio" }],
});

assertNavigationState(getNavigationState("/news"), {
  activePath: "/news",
  backFallback: "/",
  breadcrumbs: [
    { href: "/", label: "Inicio" },
    { href: "/news", label: "Noticias" },
  ],
});

assertNavigationState(getNavigationState("/datos"), {
  activePath: "/datos",
  backFallback: "/",
  breadcrumbs: [
    { href: "/", label: "Inicio" },
    { href: "/datos", label: "Datos" },
  ],
});

assertNavigationState(getNavigationState("/impacto"), {
  activePath: "/impacto",
  backFallback: "/",
  breadcrumbs: [
    { href: "/", label: "Inicio" },
    { href: "/impacto", label: "Impacto" },
  ],
});

assertNavigationState(getNavigationState("/suscribirse"), {
  activePath: "/suscribirse",
  backFallback: "/",
  breadcrumbs: [
    { href: "/", label: "Inicio" },
    { href: "/suscribirse", label: "Suscribirse" },
  ],
});

assertNavigationState(getNavigationState("/article/42"), {
  activePath: "/article",
  backFallback: "/news",
  breadcrumbs: [
    { href: "/", label: "Inicio" },
    { href: "/news", label: "Noticias" },
    { href: "/article/42", label: "Detalle" },
  ],
});

console.log("navigation tests passed");

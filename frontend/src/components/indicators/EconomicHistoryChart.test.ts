import { describe, expect, it } from "vitest";

import { parseBoliviaTimestamp } from "./EconomicHistoryChart";

describe("parseBoliviaTimestamp", () => {
  it("mantiene la hora de Bolivia al leerla de vuelta con getters UTC", () => {
    // Lightweight Charts siempre arma las etiquetas del eje con getUTCFullYear/
    // getUTCHours/etc (ver lightweight-charts.standalone.development.js). El
    // backend manda collected_at como hora de Bolivia "naive", sin offset (ver
    // _now_bolivia en src/db/repository.py) -- el epoch que devuelve esta
    // funcion tiene que reproducir esos mismos numeros al leerlo con getters
    // UTC, sin importar en que huso horario corra el navegador que lo mira.
    const epoch = parseBoliviaTimestamp("2026-09-16T21:00:00");
    const date = new Date(epoch * 1000);

    expect(date.getUTCFullYear()).toBe(2026);
    expect(date.getUTCMonth()).toBe(8); // Setiembre, 0-indexado
    expect(date.getUTCDate()).toBe(16);
    expect(date.getUTCHours()).toBe(21);
    expect(date.getUTCMinutes()).toBe(0);
  });

  it("no empuja la fecha a 'manana' cerca de medianoche", () => {
    // Caso real reportado: son las 21:00 en Bolivia y el grafico mostraba un
    // punto fechado al dia siguiente -- exactamente el desfasaje de +4h que
    // introducia `new Date(collected_at).getTime()` al dejar que el navegador
    // reinterprete el string sin offset como su propia hora local.
    const epoch = parseBoliviaTimestamp("2026-09-16T23:30:00");
    const date = new Date(epoch * 1000);

    expect(date.getUTCDate()).toBe(16);
    expect(date.getUTCHours()).toBe(23);
  });

  it("acepta el separador con espacio en vez de 'T'", () => {
    const epoch = parseBoliviaTimestamp("2026-09-16 09:05:30");
    const date = new Date(epoch * 1000);

    expect(date.getUTCDate()).toBe(16);
    expect(date.getUTCHours()).toBe(9);
    expect(date.getUTCMinutes()).toBe(5);
    expect(date.getUTCSeconds()).toBe(30);
  });

  it("cae de nuevo a un parseo normal si el formato no matchea", () => {
    // Sin segundos -- no matchea el patron esperado ("naive", con segundos),
    // asi que usa el Date(...) normal del navegador como ultimo recurso.
    const withoutSeconds = "2026-09-16T21:00";
    const epoch = parseBoliviaTimestamp(withoutSeconds);

    expect(epoch).toBe(Math.floor(new Date(withoutSeconds).getTime() / 1000));
  });
});

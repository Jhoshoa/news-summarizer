import type { EconomicIndicator } from "../../services/types";

export const formatNumber = (value?: number | null, digits = 2) => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "--";
  }

  return new Intl.NumberFormat("es-BO", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
};

export const findIndicator = (items: EconomicIndicator[], codeIncludes: string[]) =>
  items.find((item) => codeIncludes.every((part) => item.indicator_code.includes(part)));

export const findByExactCode = (items: EconomicIndicator[], code: string) =>
  items.find((item) => item.indicator_code === code);

const normalizeText = (value?: string | null) =>
  String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

const indicatorText = (item: EconomicIndicator) =>
  normalizeText(`${item.indicator_code} ${item.indicator_name} ${item.indicator_group}`);

const isTreIndicator = (item: EconomicIndicator) => {
  const text = indicatorText(item);
  return text.includes("tasa_de_referencia") || text.includes("tasa de referencia") || text.includes("tre");
};

export const findOfficialUsdIndicator = (items: EconomicIndicator[]) =>
  findByExactCode(items, "bcb_tipo_de_cambio_oficial") ??
  findByExactCode(items, "bcb_tipo_de_cambio_venta") ??
  items.find((item) => {
    const text = indicatorText(item);
    return item.source === "bcb" && item.asset === "USD" && text.includes("tipo") && text.includes("cambio");
  });

export const findUfvIndicator = (items: EconomicIndicator[]) =>
  findByExactCode(items, "bcb_unidad_de_fomento_a_la_vivienda_ufv") ??
  items.find((item) => item.source === "bcb" && item.asset === "UFV") ??
  items.find((item) => {
    const text = indicatorText(item);
    return item.source === "bcb" && !isTreIndicator(item) && text.includes("ufv");
  });

export const findGoldIndicator = (items: EconomicIndicator[]) =>
  findByExactCode(items, "bcb_cotizacion_internacional_del_oro_valor") ??
  items.find((item) => item.source === "bcb" && item.asset === "GOLD") ??
  items.find((item) => item.source === "bcb" && indicatorText(item).includes("oro"));

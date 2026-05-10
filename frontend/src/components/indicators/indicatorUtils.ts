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

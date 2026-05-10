import type { EconomicIndicator } from "../../services/types";
import { findIndicator, formatNumber } from "./indicatorUtils";

type SecondaryIndicatorsProps = {
  indicators: EconomicIndicator[];
};

type MiniIndicatorProps = {
  label: string;
  value: string;
  source?: string;
};

const MiniIndicator = ({ label, value, source = "BCB" }: MiniIndicatorProps) => (
  <article className="mini-indicator">
    <span>{label}</span>
    <strong>{value}</strong>
    <small>{source}</small>
  </article>
);

export const SecondaryIndicators = ({ indicators }: SecondaryIndicatorsProps) => {
  const ufv = findIndicator(indicators, ["ufv"]);
  const gold = findIndicator(indicators, ["oro"]);
  const treMn = findIndicator(indicators, ["tre", "mn"]);
  const treMe = findIndicator(indicators, ["tre", "me"]);

  return (
    <section className="mini-grid" aria-label="Indicadores BCB">
      <MiniIndicator label="UFV" value={`Bs ${formatNumber(ufv?.value, 5)}`} />
      <MiniIndicator label="Oro" value={`USD ${formatNumber(gold?.value, 2)}`} source="O.T.F." />
      <MiniIndicator label="TRE MN" value={`${formatNumber(treMn?.value, 2)}%`} />
      <MiniIndicator label="TRE ME" value={`${formatNumber(treMe?.value, 2)}%`} />
    </section>
  );
};

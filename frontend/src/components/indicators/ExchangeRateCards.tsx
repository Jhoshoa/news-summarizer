import type { EconomicIndicator } from "../../services/types";
import { findByExactCode, findOfficialUsdIndicator, formatNumber } from "./indicatorUtils";

type ExchangeRateCardsProps = {
  indicators: EconomicIndicator[];
};

type RateCardProps = {
  title: string;
  subtitle: string;
  value?: number;
  valueLabel?: string;
  buy?: number;
  sell?: number;
};

const RateCard = ({ title, subtitle, value, valueLabel = "Valor", buy, sell }: RateCardProps) => (
  <article className="market" id="indicadores">
    <strong>{title}</strong>
    {value !== undefined ? (
      <div className="rate-single">
        <em>{valueLabel}</em>
        <b>Bs {formatNumber(value)}</b>
      </div>
    ) : (
      <div className="rate-pair">
        <div>
          <em>Compra</em>
          <b>Bs {formatNumber(buy)}</b>
        </div>
        <div>
          <em>Venta</em>
          <b>Bs {formatNumber(sell)}</b>
        </div>
      </div>
    )}
    <small>{subtitle}</small>
  </article>
);

export const ExchangeRateCards = ({ indicators }: ExchangeRateCardsProps) => {
  const officialRate = findOfficialUsdIndicator(indicators)?.value;
  const p2pBuy = findByExactCode(indicators, "binance_p2p_usdt_bob_buy")?.value;
  const p2pSell = findByExactCode(indicators, "binance_p2p_usdt_bob_sell")?.value;

  return (
    <section className="markets" aria-label="Tipos de cambio">
      <RateCard title="Dolar oficial" subtitle="BCB - TCO" value={officialRate} valueLabel="Oficial" />
      <RateCard title="P2P Binance" subtitle="Mercado P2P" buy={p2pBuy} sell={p2pSell} />
    </section>
  );
};

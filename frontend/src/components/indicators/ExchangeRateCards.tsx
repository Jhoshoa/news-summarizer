import type { EconomicIndicator } from "../../services/types";
import { findByExactCode, formatNumber } from "./indicatorUtils";

type ExchangeRateCardsProps = {
  indicators: EconomicIndicator[];
};

type RateCardProps = {
  title: string;
  subtitle: string;
  buy?: number;
  sell?: number;
};

const RateCard = ({ title, subtitle, buy, sell }: RateCardProps) => (
  <article className="market" id="indicadores">
    <strong>{title}</strong>
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
    <small>{subtitle}</small>
  </article>
);

export const ExchangeRateCards = ({ indicators }: ExchangeRateCardsProps) => {
  const officialBuy = findByExactCode(indicators, "bcb_tipo_de_cambio_compra")?.value;
  const officialSell = findByExactCode(indicators, "bcb_tipo_de_cambio_venta")?.value;
  const referenceBuy = findByExactCode(
    indicators,
    "bcb_valor_referencial_del_dolar_estadounidense_compra",
  )?.value;
  const referenceSell = findByExactCode(
    indicators,
    "bcb_valor_referencial_del_dolar_estadounidense_venta",
  )?.value;
  const p2pBuy = findByExactCode(indicators, "binance_p2p_usdt_bob_buy")?.value;
  const p2pSell = findByExactCode(indicators, "binance_p2p_usdt_bob_sell")?.value;

  return (
    <section className="markets" aria-label="Tipos de cambio">
      <RateCard title="Tipo oficial" subtitle="BCB - dolar USA" buy={officialBuy} sell={officialSell} />
      <RateCard
        title="Referencial BCB"
        subtitle="Operaciones EIF"
        buy={referenceBuy}
        sell={referenceSell}
      />
      <RateCard title="P2P Binance" subtitle="Mercado P2P" buy={p2pBuy} sell={p2pSell} />
    </section>
  );
};

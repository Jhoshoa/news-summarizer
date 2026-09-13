import { memo } from "react";

import { formatNumber, findByExactCode, findOfficialUsdIndicator } from "../indicators/indicatorUtils";
import { useGetEconomicIndicatorsQuery, useGetImpactMetricsQuery } from "../../services/api";

const formatEdition = (isoDate?: string) => {
  if (!isoDate) {
    return null;
  }
  const parsed = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  const day = String(parsed.getDate()).padStart(2, "0");
  const month = parsed.toLocaleDateString("es-BO", { month: "short" }).replace(".", "").toUpperCase();
  return `${day}·${month}·${parsed.getFullYear()}`;
};

const TickerStripComponent = () => {
  const { data: impact } = useGetImpactMetricsQuery({ fallback_to_latest: true });
  const { data: indicators } = useGetEconomicIndicatorsQuery();

  const items: string[] = [];

  const edition = formatEdition(impact?.date);
  if (edition) {
    items.push(`EDICION ${edition}`);
  }
  if (impact?.has_data) {
    items.push(`${formatNumber(impact.collected_articles, 0)} RECOLECTADAS`);
    items.push(`${formatNumber(impact.summaries, 0)} BRIEFS`);
    items.push(`${formatNumber(impact.reduction_rate * 100, 1)}% REDUCCION`);
  }

  const officialRate = findOfficialUsdIndicator(indicators?.items ?? [])?.value;
  if (officialRate !== undefined) {
    items.push(`BCB ${formatNumber(officialRate)}`);
  }

  const p2pBuy = findByExactCode(indicators?.items ?? [], "binance_p2p_usdt_bob_buy")?.value;
  const p2pSell = findByExactCode(indicators?.items ?? [], "binance_p2p_usdt_bob_sell")?.value;
  if (p2pBuy !== undefined && p2pSell !== undefined) {
    items.push(`P2P ${formatNumber(p2pBuy)} / ${formatNumber(p2pSell)}`);
  }

  if (!items.length) {
    return null;
  }

  const track = [...items, ...items];

  return (
    <div aria-hidden="true" className="wire">
      <div className="wire-track">
        {track.map((item, index) => (
          <span key={`${item}-${index}`}>{item}</span>
        ))}
      </div>
    </div>
  );
};

export const TickerStrip = memo(TickerStripComponent);

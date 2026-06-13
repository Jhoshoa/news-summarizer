import { useCallback, useMemo, useState } from "react";

import { usePageRefreshControl } from "../app/refreshControl";
import { ExchangeRateCards } from "../components/indicators/ExchangeRateCards";
import { findByExactCode, formatNumber } from "../components/indicators/indicatorUtils";
import { SummaryCard } from "../components/news/SummaryCard";
import { MarketSkeletons, PanelSkeleton, SummaryCardSkeleton } from "../components/ui/Skeleton";
import {
  useGetEconomicIndicatorsQuery,
  useGetSummariesQuery,
  useGetWeatherQuery,
  useRefreshEconomicIndicatorsMutation,
} from "../services/api";
import type { EconomicIndicator } from "../services/types";

const getNumber = (value: unknown) => {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
};

const formatMetric = (value: unknown, suffix = "", digits = 1) => {
  const numberValue = getNumber(value);
  if (numberValue === null) {
    return "--";
  }

  return `${formatNumber(numberValue, digits)}${suffix}`;
};

const CurrencySpread = ({ indicators }: { indicators: EconomicIndicator[] }) => {
  const officialSell = findByExactCode(indicators, "bcb_tipo_de_cambio_venta")?.value;
  const p2pSell = findByExactCode(indicators, "binance_p2p_usdt_bob_sell")?.value;
  const referenceSell = findByExactCode(
    indicators,
    "bcb_valor_referencial_del_dolar_estadounidense_venta",
  )?.value;
  const spread = p2pSell && officialSell ? p2pSell - officialSell : null;
  const referenceSpread = referenceSell && officialSell ? referenceSell - officialSell : null;

  return (
    <section className="data-panel">
      <span className="panel-title">Brecha cambiaria</span>
      <div className="hero-metric">
        <strong>Bs {formatNumber(spread, 2)}</strong>
        <span>P2P venta menos oficial venta</span>
      </div>
      <div className="metric-list">
        <div>
          <span>Referencial vs oficial</span>
          <strong>Bs {formatNumber(referenceSpread, 2)}</strong>
        </div>
        <div>
          <span>Oficial venta</span>
          <strong>Bs {formatNumber(officialSell, 2)}</strong>
        </div>
        <div>
          <span>P2P venta</span>
          <strong>Bs {formatNumber(p2pSell, 2)}</strong>
        </div>
      </div>
    </section>
  );
};

const departments: Array<{ label: string; location: string }> = [
  { label: "La Paz", location: "La Paz" },
  { label: "Santa Cruz", location: "Santa Cruz" },
  { label: "Cochabamba", location: "Cochabamba" },
  { label: "Oruro", location: "Oruro" },
  { label: "Potosi", location: "Potosi" },
  { label: "Tarija", location: "Tarija" },
  { label: "Chuquisaca", location: "Sucre" },
  { label: "Beni", location: "Trinidad" },
  { label: "Pando", location: "Cobija" },
];

export const DataPage = () => {
  const [selectedDept, setSelectedDept] = useState("La Paz");
  const selectedLocation = departments.find((d) => d.label === selectedDept)?.location ?? "La Paz";
  const { data: indicatorsData, isFetching: isFetchingIndicators } = useGetEconomicIndicatorsQuery();
  const { data: weather, isFetching: isFetchingWeather } = useGetWeatherQuery(selectedLocation);
  const { data: summariesData, isFetching: isFetchingSummaries } = useGetSummariesQuery({
    fallback_to_latest: true,
    page_size: 3,
  });
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();

  const indicators = indicatorsData?.items ?? [];
  const summaries = summariesData?.items ?? [];
  const current = weather?.current ?? {};
  const elevation = getNumber(weather?.raw_payload.elevation);
  const timezone = String(weather?.raw_payload.timezone ?? "America/La_Paz");
  const city = weather?.location.name ?? selectedLocation;
  const showEconomySkeleton = isFetchingIndicators;
  const showWeatherSkeleton = isFetchingWeather;

  const handleRefresh = useCallback(() => {
    void refreshIndicators();
  }, [refreshIndicators]);

  const refreshControl = useMemo(
    () => ({
      isRefreshing: isRefreshing || isFetchingIndicators,
      onRefresh: handleRefresh,
    }),
    [handleRefresh, isFetchingIndicators, isRefreshing],
  );
  usePageRefreshControl(refreshControl);

  return (
    <>
      <section className="data-page">
        <header className="data-hero">
          <div>
            <h1>Datos esenciales</h1>
          </div>
        </header>

        <section className="data-context-layout">
          <div className="data-context-main">
            <section className="data-section">
              <div className="panel-heading">
                <span className="panel-title">Economia esencial</span>
              </div>
              {showEconomySkeleton ? <MarketSkeletons /> : <ExchangeRateCards indicators={indicators} />}
              {showEconomySkeleton ? (
                <PanelSkeleton />
              ) : (
                <CurrencySpread indicators={indicators} />
              )}
            </section>

            <section className="data-section">
              <div className="panel-heading">
                <span className="panel-title">Clima local</span>
              </div>
              <div className="category-tabs" aria-label="Departamentos">
                {departments.map((dept) => (
                  <a
                    key={dept.label}
                    href="#"
                    role="button"
                    className={dept.label === selectedDept ? "active" : ""}
                    onClick={(e) => {
                      e.preventDefault();
                      setSelectedDept(dept.label);
                    }}
                  >
                    {dept.label}
                  </a>
                ))}
              </div>
              {showWeatherSkeleton ? (
                <PanelSkeleton />
              ) : (
                <section className="data-panel context-weather-card">
                  <div>
                    <span className="panel-title">{city}</span>
                    <div className="weather-temp">{formatMetric(current.temperature_2m, "C", 1)}</div>
                    <p>Temperatura actual</p>
                  </div>
                  <div className="metric-list">
                    <div>
                      <span>Radiacion UV</span>
                      <strong>{formatMetric(weather?.today.uv_index_max, "", 1)}</strong>
                    </div>
                    <div>
                      <span>Humedad</span>
                      <strong>{formatMetric(current.relative_humidity_2m, "%", 0)}</strong>
                    </div>
                    <div>
                      <span>Viento</span>
                      <strong>{formatMetric(current.wind_speed_10m, " km/h", 1)}</strong>
                    </div>
                  </div>
                  <small>
                    {timezone} {elevation ? `- elevacion ${formatNumber(elevation, 0)} m` : ""}
                  </small>
                </section>
              )}
            </section>
          </div>

          <aside className="data-context-sidebar">
            <div className="data-briefs-list">
              {isFetchingSummaries
                ? Array.from({ length: 3 }, (_, index) => <SummaryCardSkeleton key={index} />)
                : summaries.slice(0, 3).map((summary) => (
                    <SummaryCard key={summary.id ?? summary.title} summary={summary} />
                  ))}
            </div>
          </aside>
        </section>
      </section>
    </>
  );
};

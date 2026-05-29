import { useCallback, useMemo, useState } from "react";

import { usePageRefreshControl } from "../app/refreshControl";
import { ExchangeRateCards } from "../components/indicators/ExchangeRateCards";
import { findByExactCode, formatNumber } from "../components/indicators/indicatorUtils";
import { SecondaryIndicators } from "../components/indicators/SecondaryIndicators";
import { MarketSkeletons, MiniIndicatorSkeletons, PanelSkeleton, TableSkeleton } from "../components/ui/Skeleton";
import {
  useGetEconomicIndicatorsQuery,
  useGetWeatherLocationsQuery,
  useGetWeatherQuery,
  useRefreshEconomicIndicatorsMutation,
} from "../services/api";
import type { EconomicIndicator, WeatherResponse } from "../services/types";
import { formatPublishedDate } from "../utils/date";

type DataTab = "economia" | "clima";

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

const latestCollectedAt = (items: EconomicIndicator[]) =>
  {
    const dates = items
    .map((item) => item.collected_at)
    .filter(Boolean)
    .sort();

    return dates[dates.length - 1];
  };

const IndicatorTable = ({ indicators }: { indicators: EconomicIndicator[] }) => (
  <section className="data-panel wide-panel">
    <div className="panel-heading">
      <span className="panel-title">Todos los indicadores</span>
      <p>Valores disponibles desde BCB y mercado P2P, ordenados por grupo y fuente.</p>
    </div>
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Indicador</th>
            <th>Grupo</th>
            <th>Fuente</th>
            <th>Valor</th>
            <th>Unidad</th>
          </tr>
        </thead>
        <tbody>
          {indicators.map((item) => (
            <tr key={`${item.source}-${item.indicator_code}-${item.side ?? ""}`}>
              <td>{item.indicator_name}</td>
              <td>{item.indicator_group}</td>
              <td>{item.source}</td>
              <td>{formatNumber(item.value, item.indicator_code.includes("ufv") ? 5 : 2)}</td>
              <td>{item.unit ?? item.currency ?? item.asset ?? "--"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </section>
);

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

const WeatherHourlyBars = ({ weather }: { weather?: WeatherResponse }) => {
  const hourly = weather?.raw_payload.hourly as
    | {
        time?: string[];
        uv_index?: number[];
        shortwave_radiation?: number[];
        direct_radiation?: number[];
      }
    | undefined;
  const rows = useMemo(() => {
    if (!hourly?.time?.length) {
      return [];
    }

    return hourly.time.map((time, index) => ({
      time,
      uv: hourly.uv_index?.[index] ?? 0,
      shortwave: hourly.shortwave_radiation?.[index] ?? 0,
      direct: hourly.direct_radiation?.[index] ?? 0,
    }));
  }, [hourly]);
  const maxRadiation = Math.max(...rows.map((row) => row.shortwave), 1);

  return (
    <section className="data-panel wide-panel">
      <div className="panel-heading">
        <span className="panel-title">Radiacion por hora</span>
        <p>Lectura horaria de UV, radiacion solar corta y radiacion directa.</p>
      </div>
      <div className="hourly-grid">
        {rows.map((row) => (
          <div className="hour-bar" key={row.time}>
            <span>{row.time.slice(11, 16)}</span>
            <div>
              <i style={{ height: `${Math.max((row.shortwave / maxRadiation) * 100, 3)}%` }} />
            </div>
            <strong>{formatNumber(row.uv, 1)}</strong>
          </div>
        ))}
      </div>
    </section>
  );
};

export const DataPage = () => {
  const [activeTab, setActiveTab] = useState<DataTab>("economia");
  const [selectedLocation, setSelectedLocation] = useState("La Paz");
  const { data: indicatorsData, isFetching: isFetchingIndicators } = useGetEconomicIndicatorsQuery();
  const { data: locationsData, isFetching: isFetchingLocations } = useGetWeatherLocationsQuery();
  const { data: weather, isFetching: isFetchingWeather } = useGetWeatherQuery(selectedLocation);
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();

  const indicators = indicatorsData?.items ?? [];
  const collectedAt = latestCollectedAt(indicators);
  const current = weather?.current ?? {};
  const elevation = getNumber(weather?.raw_payload.elevation);
  const timezone = String(weather?.raw_payload.timezone ?? "America/La_Paz");
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
            <span className="eyebrow">Datos Bolivia IA</span>
            <h1>Indicadores economicos y clima en una vista operativa</h1>
            <p>
              Consulta tipos de cambio, UFV, oro, tasas TRE, clima local, radiacion UV y datos
              horarios para los departamentos disponibles.
            </p>
          </div>
          <div className="data-status-card">
            <span>Ultima actualizacion</span>
            {showEconomySkeleton ? (
              <>
                <span className="skeleton-block skeleton-line skeleton-line-lg" aria-hidden="true" />
                <span className="skeleton-block skeleton-line skeleton-line-md" aria-hidden="true" />
              </>
            ) : (
              <>
                <strong>{collectedAt ? formatPublishedDate(collectedAt) : "Sin datos"}</strong>
                <small>{indicators.length} indicadores economicos cargados</small>
              </>
            )}
          </div>
        </header>

        <div className="data-tabs" role="tablist" aria-label="Datos disponibles">
          <button
            className={activeTab === "economia" ? "active" : ""}
            type="button"
            onClick={() => setActiveTab("economia")}
          >
            Economia
          </button>
          <button
            className={activeTab === "clima" ? "active" : ""}
            type="button"
            onClick={() => setActiveTab("clima")}
          >
            Clima y radiacion
          </button>
        </div>

        {activeTab === "economia" ? (
          <section className="data-section">
            {showEconomySkeleton ? <MarketSkeletons /> : <ExchangeRateCards indicators={indicators} />}
            <div className="data-grid">
              {showEconomySkeleton ? (
                <>
                  <PanelSkeleton />
                  <PanelSkeleton />
                </>
              ) : (
                <>
                  <CurrencySpread indicators={indicators} />
                  <section className="data-panel">
                    <span className="panel-title">Fuentes</span>
                    <div className="metric-list">
                      <div>
                        <span>Banco Central de Bolivia</span>
                        <strong>BCB</strong>
                      </div>
                      <div>
                        <span>Mercado paralelo digital</span>
                        <strong>Binance P2P</strong>
                      </div>
                      <div>
                        <span>Frecuencia sugerida</span>
                        <strong>1 hora</strong>
                      </div>
                    </div>
                  </section>
                </>
              )}
            </div>
            {showEconomySkeleton ? <MiniIndicatorSkeletons /> : <SecondaryIndicators indicators={indicators} />}
            {showEconomySkeleton ? <TableSkeleton /> : <IndicatorTable indicators={indicators} />}
          </section>
        ) : (
          <section className="data-section">
            <div className="location-strip">
              {isFetchingLocations
                ? Array.from({ length: 5 }, (_, index) => (
                    <span className="skeleton-block skeleton-chip" key={index} aria-hidden="true" />
                  ))
                : (locationsData?.items ?? []).map((location) => (
                    <button
                      className={selectedLocation === location.name ? "active" : ""}
                      key={location.key}
                      type="button"
                      onClick={() => setSelectedLocation(location.name)}
                    >
                      {location.name}
                    </button>
                  ))}
            </div>

            <div className="weather-dashboard" aria-busy={showWeatherSkeleton}>
              {showWeatherSkeleton ? (
                <>
                  <PanelSkeleton />
                  <PanelSkeleton />
                  <PanelSkeleton />
                </>
              ) : (
                <>
                  <section className="data-panel weather-spotlight">
                    <span className="panel-title">{weather?.location.name ?? selectedLocation}</span>
                    <div className="weather-temp">{formatMetric(current.temperature_2m, "C", 1)}</div>
                    <p>
                      Humedad {formatMetric(current.relative_humidity_2m, "%", 0)} - viento{" "}
                      {formatMetric(current.wind_speed_10m, " km/h", 1)}
                    </p>
                    <small>
                      {timezone} {elevation ? `- elevacion ${formatNumber(elevation, 0)} m` : ""}
                    </small>
                  </section>

                  <section className="data-panel">
                    <span className="panel-title">Rango del dia</span>
                    <div className="metric-list">
                      <div>
                        <span>Maxima</span>
                        <strong>{formatMetric(weather?.today.temperature_max, "C", 1)}</strong>
                      </div>
                      <div>
                        <span>Minima</span>
                        <strong>{formatMetric(weather?.today.temperature_min, "C", 1)}</strong>
                      </div>
                      <div>
                        <span>Precipitacion</span>
                        <strong>{formatMetric(weather?.today.precipitation_sum, " mm", 1)}</strong>
                      </div>
                    </div>
                  </section>

                  <section className="data-panel">
                    <span className="panel-title">Radiacion actual</span>
                    <div className="metric-list">
                      <div>
                        <span>UV actual</span>
                        <strong>{formatMetric(weather?.radiation.uv_index, "", 1)}</strong>
                      </div>
                      <div>
                        <span>UV maximo</span>
                        <strong>{formatMetric(weather?.today.uv_index_max, "", 1)}</strong>
                      </div>
                      <div>
                        <span>Solar directa</span>
                        <strong>{formatMetric(weather?.radiation.direct_radiation, " W/m2", 0)}</strong>
                      </div>
                    </div>
                  </section>
                </>
              )}
            </div>

            {showWeatherSkeleton ? <TableSkeleton /> : <WeatherHourlyBars weather={weather} />}
          </section>
        )}
      </section>
    </>
  );
};

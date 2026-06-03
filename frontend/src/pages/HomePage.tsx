import { useCallback, useMemo } from "react";

import { usePageRefreshControl } from "../app/refreshControl";
import { ExchangeRateCards } from "../components/indicators/ExchangeRateCards";
import { findByExactCode, formatNumber } from "../components/indicators/indicatorUtils";
import { SecondaryIndicators } from "../components/indicators/SecondaryIndicators";
import { NewsCard } from "../components/news/NewsCard";
import { PhoneBrief } from "../components/news/PhoneBrief";
import { SummaryCard } from "../components/news/SummaryCard";
import {
  MarketSkeletons,
  MiniIndicatorSkeletons,
  NewsCardSkeleton,
  PanelSkeleton,
  SummaryCardSkeleton,
} from "../components/ui/Skeleton";
import { WeatherPanel } from "../components/weather/WeatherPanel";
import {
  useGetArticlesQuery,
  useGetEconomicIndicatorsQuery,
  useGetSummariesQuery,
  useGetWeatherQuery,
  useRefreshEconomicIndicatorsMutation,
  useTriggerSummaryMutation,
} from "../services/api";

const departments = [
  "La Paz",
  "Santa Cruz",
  "Cochabamba",
  "Oruro",
  "Potosi",
  "Tarija",
  "Beni",
  "Chuquisaca",
  "Pando",
];

const formatContentDate = (value?: string | null) => {
  if (!value) {
    return "";
  }

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat("es-BO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
};

export const HomePage = () => {
  const { data: indicatorsData, isFetching: isFetchingIndicators } = useGetEconomicIndicatorsQuery();
  const { data: weather, isFetching: isFetchingWeather } = useGetWeatherQuery();
  const { data: articlesData, isFetching: isFetchingArticles } = useGetArticlesQuery({
    limit: 8,
    fallback_to_latest: true,
    exclude_summarized: true,
  });
  const { data: summariesData, isFetching: isFetchingSummaries } = useGetSummariesQuery({
    fallback_to_latest: true,
  });
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();
  const [triggerSummary, { isLoading: isTriggeringSummary }] = useTriggerSummaryMutation();

  const indicators = indicatorsData?.items ?? [];
  const articles = useMemo(() => articlesData?.items ?? [], [articlesData?.items]);
  const summaries = useMemo(() => summariesData?.items ?? [], [summariesData?.items]);
  const headline = summaries[0]?.title ?? "Menos ruido informativo, mas claridad local";
  const fallbackDate = summariesData?.is_fallback
    ? summariesData.date
    : articlesData?.is_fallback
      ? articlesData.date
      : null;
  const fallbackDateLabel = formatContentDate(fallbackDate);
  const p2pBuy = formatNumber(findByExactCode(indicators, "binance_p2p_usdt_bob_buy")?.value);
  const p2pSell = formatNumber(findByExactCode(indicators, "binance_p2p_usdt_bob_sell")?.value);
  const showIndicatorSkeleton = isFetchingIndicators;
  const showArticleSkeleton = isFetchingArticles;
  const showSummarySkeleton = isFetchingSummaries;
  const showWeatherSkeleton = isFetchingWeather;
  const showPhoneSkeleton = showArticleSkeleton || showSummarySkeleton || showIndicatorSkeleton || showWeatherSkeleton;

  const featuredArticles = useMemo(() => articles.slice(0, 3), [articles]);
  const featuredSummaries = useMemo(() => summaries.slice(0, 3), [summaries]);

  const handleRefresh = useCallback(() => {
    void Promise.all([
      refreshIndicators().unwrap(),
      triggerSummary({ refresh: true, time_of_day: "manual" }).unwrap(),
    ]).catch((error) => {
      console.error("Error actualizando portada", error);
    });
  }, [refreshIndicators, triggerSummary]);

  const refreshControl = useMemo(
    () => ({
      isRefreshing: isRefreshing || isFetchingIndicators || isTriggeringSummary,
      onRefresh: handleRefresh,
    }),
    [handleRefresh, isFetchingIndicators, isRefreshing, isTriggeringSummary],
  );
  usePageRefreshControl(refreshControl);

  return (
    <>
      <section className="home-layout">
        {showPhoneSkeleton ? (
          <aside className="phone-brief" aria-label="Cargando portada movil">
            <div className="phone-screen skeleton-phone" aria-hidden="true">
              <span className="skeleton-block skeleton-line skeleton-line-sm" />
              <span className="skeleton-block skeleton-title" />
              <span className="skeleton-block skeleton-line" />
              <span className="skeleton-block skeleton-line skeleton-line-md" />
              {Array.from({ length: 4 }, (_, index) => (
                <span className="skeleton-block skeleton-phone-row" key={index} />
              ))}
            </div>
          </aside>
        ) : (
          <PhoneBrief
            headline={headline}
            articles={featuredArticles}
            p2pBuy={p2pBuy}
            p2pSell={p2pSell}
            weather={weather}
          />
        )}

        <section className="content-column">
          <section className="hero-panel" id="ultimo">
            <div className="hero-art">
              <span>EcoBrief Bolivia</span>
              <h1>Noticias locales resumidas con menos ruido y menos desperdicio digital</h1>
            </div>
          </section>

          {showIndicatorSkeleton ? <MarketSkeletons /> : <ExchangeRateCards indicators={indicators} />}
          {showIndicatorSkeleton ? <MiniIndicatorSkeletons /> : <SecondaryIndicators indicators={indicators} />}

          <section className="lower-grid">
            <div className="news-list">
              {fallbackDateLabel && (
                <p className="form-notice">
                  No hay noticias de hoy todavia. Mostrando ultimas disponibles del {fallbackDateLabel}.
                </p>
              )}
              <div className="section-label">Briefs EcoBrief</div>
              {showSummarySkeleton
                ? Array.from({ length: 3 }, (_, index) => <SummaryCardSkeleton key={index} />)
                : featuredSummaries.map((summary) => (
                    <SummaryCard key={summary.id ?? summary.title} summary={summary} />
                  ))}
              {!showSummarySkeleton && featuredSummaries.length === 0 && (
                <section className="empty-state compact">
                  <span className="panel-title">Sin briefs disponibles</span>
                  <p>Actualiza la portada para sintetizar las noticias recolectadas.</p>
                </section>
              )}
              <div className="section-label">Noticias sin resumir</div>
              {showArticleSkeleton
                ? Array.from({ length: 2 }, (_, index) => <NewsCardSkeleton key={index} />)
                : featuredArticles.slice(0, 2).map((article) => (
                    <NewsCard key={article.id} article={article} />
                  ))}
              {!showArticleSkeleton && featuredArticles.length === 0 && (
                <section className="empty-state compact">
                  <span className="panel-title">Sin noticias recolectadas</span>
                  <p>Presiona actualizar para recolectar noticias desde las fuentes configuradas.</p>
                </section>
              )}
            </div>

            <aside className="side-stack">
              <section className="departments-card" id="departamentos">
                <div className="panel-title">Departamentos</div>
                <div className="chips">
                  {departments.map((department) => (
                    <span key={department}>{department}</span>
                  ))}
                </div>
              </section>
              {showWeatherSkeleton ? <PanelSkeleton /> : <WeatherPanel weather={weather} />}
            </aside>
          </section>
        </section>
      </section>
    </>
  );
};

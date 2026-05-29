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
import { departments, mockArticles, mockSummaries } from "../data/mockNews";
import {
  useGetArticlesQuery,
  useGetEconomicIndicatorsQuery,
  useGetSummariesQuery,
  useGetWeatherQuery,
  useRefreshEconomicIndicatorsMutation,
  useTriggerSummaryMutation,
} from "../services/api";

export const HomePage = () => {
  const { data: indicatorsData, isFetching: isFetchingIndicators } = useGetEconomicIndicatorsQuery();
  const { data: weather, isFetching: isFetchingWeather } = useGetWeatherQuery();
  const { data: articlesData, isFetching: isFetchingArticles } = useGetArticlesQuery({ limit: 8 });
  const { data: summariesData, isFetching: isFetchingSummaries } = useGetSummariesQuery();
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();
  const [triggerSummary, { isLoading: isTriggeringSummary }] = useTriggerSummaryMutation();

  const indicators = indicatorsData?.items ?? [];
  const articles = articlesData?.items.length ? articlesData.items : mockArticles;
  const summaries = summariesData?.items.length ? summariesData.items : mockSummaries;
  const headline = summaries[0]?.title ?? "Bolivia en titulares, contexto y datos locales";
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
              <span>Portada nacional</span>
              <h1>Noticias actuales con resumen IA, fuente visible e indicadores clave</h1>
            </div>
          </section>

          {showIndicatorSkeleton ? <MarketSkeletons /> : <ExchangeRateCards indicators={indicators} />}
          {showIndicatorSkeleton ? <MiniIndicatorSkeletons /> : <SecondaryIndicators indicators={indicators} />}

          <section className="lower-grid">
            <div className="news-list">
              <div className="section-label">Resumenes IA</div>
              {showSummarySkeleton
                ? Array.from({ length: 3 }, (_, index) => <SummaryCardSkeleton key={index} />)
                : featuredSummaries.map((summary) => (
                    <SummaryCard key={summary.id ?? summary.title} summary={summary} />
                  ))}
              <div className="section-label">Mas noticias</div>
              {showArticleSkeleton
                ? Array.from({ length: 2 }, (_, index) => <NewsCardSkeleton key={index} />)
                : featuredArticles.slice(0, 2).map((article) => (
                    <NewsCard key={article.id} article={article} />
                  ))}
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

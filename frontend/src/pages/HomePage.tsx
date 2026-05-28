import { useMemo } from "react";

import { ExchangeRateCards } from "../components/indicators/ExchangeRateCards";
import { findByExactCode, formatNumber } from "../components/indicators/indicatorUtils";
import { SecondaryIndicators } from "../components/indicators/SecondaryIndicators";
import { AppShell } from "../components/layout/AppShell";
import { NewsCard } from "../components/news/NewsCard";
import { PhoneBrief } from "../components/news/PhoneBrief";
import { SummaryCard } from "../components/news/SummaryCard";
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
  const { data: weather } = useGetWeatherQuery();
  const { data: articlesData } = useGetArticlesQuery({ limit: 8 });
  const { data: summariesData } = useGetSummariesQuery();
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();
  const [triggerSummary, { isLoading: isTriggeringSummary }] = useTriggerSummaryMutation();

  const indicators = indicatorsData?.items ?? [];
  const articles = articlesData?.items.length ? articlesData.items : mockArticles;
  const summaries = summariesData?.items.length ? summariesData.items : mockSummaries;
  const headline = summaries[0]?.title ?? "Bolivia en titulares, contexto y datos locales";
  const p2pBuy = formatNumber(findByExactCode(indicators, "binance_p2p_usdt_bob_buy")?.value);
  const p2pSell = formatNumber(findByExactCode(indicators, "binance_p2p_usdt_bob_sell")?.value);

  const featuredArticles = useMemo(() => articles.slice(0, 3), [articles]);
  const featuredSummaries = useMemo(() => summaries.slice(0, 3), [summaries]);

  const handleRefresh = () => {
    void Promise.all([
      refreshIndicators().unwrap(),
      triggerSummary({ refresh: true, time_of_day: "manual" }).unwrap(),
    ]).catch((error) => {
      console.error("Error actualizando portada", error);
    });
  };

  return (
    <AppShell
      isRefreshing={isRefreshing || isFetchingIndicators || isTriggeringSummary}
      onRefresh={handleRefresh}
    >
      <section className="home-layout">
        <PhoneBrief
          headline={headline}
          articles={featuredArticles}
          p2pBuy={p2pBuy}
          p2pSell={p2pSell}
          weather={weather}
        />

        <section className="content-column">
          <section className="hero-panel" id="ultimo">
            <div className="hero-art">
              <span>Portada nacional</span>
              <h1>Noticias actuales con resumen IA, fuente visible e indicadores clave</h1>
            </div>
          </section>

          <ExchangeRateCards indicators={indicators} />
          <SecondaryIndicators indicators={indicators} />

          <section className="lower-grid">
            <div className="news-list">
              <div className="section-label">Resumenes IA</div>
              {featuredSummaries.map((summary) => (
                <SummaryCard key={summary.id ?? summary.title} summary={summary} />
              ))}
              <div className="section-label">Mas noticias</div>
              {featuredArticles.slice(0, 2).map((article) => (
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
              <WeatherPanel weather={weather} />
            </aside>
          </section>
        </section>
      </section>
    </AppShell>
  );
};

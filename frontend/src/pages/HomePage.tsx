import { useCallback, useMemo } from "react";

import { Link } from "../app/router";
import { usePageRefreshControl } from "../app/refreshControl";
import { ImpactMetricsPanel } from "../components/impact/ImpactMetricsPanel";
import { ExchangeRateCards } from "../components/indicators/ExchangeRateCards";
import { SecondaryIndicators } from "../components/indicators/SecondaryIndicators";
import { ArticleImage } from "../components/news/ArticleImage";
import { NewsCard } from "../components/news/NewsCard";
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
  useGetImpactMetricsQuery,
  useGetSummariesQuery,
  useGetWeatherQuery,
  useRefreshEconomicIndicatorsMutation,
  useTriggerSummaryMutation,
} from "../services/api";
import type { Article, Summary } from "../services/types";
import { formatPublishedDate } from "../utils/date";
import { buildContextualSummary, cleanGeneratedText } from "../utils/summaryText";

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

const hasImage = (item: Pick<Article | Summary, "image">) => Boolean(item.image?.trim());

const prioritizeImages = <T extends Pick<Article | Summary, "image">>(items: T[]) => [
  ...items.filter(hasImage),
  ...items.filter((item) => !hasImage(item)),
];

const FeaturedSummary = ({ summary }: { summary: Summary }) => {
  const href = summary.article_id ? `/article/${summary.article_id}` : summary.url || "#";
  const title = cleanGeneratedText(summary.title);
  const summaryText = buildContextualSummary(summary.summary, summary.article_description);
  const fact = summary.fact ? cleanGeneratedText(summary.fact) : "";
  const content = (
    <>
      <ArticleImage image={summary.image} alt={title} />
      <div className="featured-summary-copy">
        <div className="card-meta-row">
          <span className="eyebrow">
            {summary.source ?? "EcoBrief Bolivia"} - {summary.category}
          </span>
          <span className="status-badge summarized">Resumido IA</span>
        </div>
        <time className="published-date" dateTime={summary.published_at ?? summary.created_at ?? undefined}>
          {formatPublishedDate(summary.published_at ?? summary.created_at)}
        </time>
        <h2>{title}</h2>
        <p>{summaryText}</p>
        {fact && <small>{fact}</small>}
      </div>
    </>
  );

  if (summary.article_id) {
    return (
      <Link className="featured-summary card-link" href={href}>
        {content}
      </Link>
    );
  }

  return (
    <a className="featured-summary card-link" href={href}>
      {content}
    </a>
  );
};

export const HomePage = () => {
  const { data: indicatorsData, isFetching: isFetchingIndicators } = useGetEconomicIndicatorsQuery();
  const { data: weather, isFetching: isFetchingWeather } = useGetWeatherQuery();
  const {
    data: impactMetrics,
    error: impactMetricsError,
    isFetching: isFetchingImpactMetrics,
  } = useGetImpactMetricsQuery({ fallback_to_latest: true });
  const { data: articlesData, isFetching: isFetchingArticles } = useGetArticlesQuery({
    limit: 20,
    fallback_to_latest: true,
  });
  const { data: summariesData, isFetching: isFetchingSummaries } = useGetSummariesQuery({
    fallback_to_latest: true,
    page_size: 20,
  });
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();
  const [triggerSummary, { isLoading: isTriggeringSummary }] = useTriggerSummaryMutation();

  const indicators = indicatorsData?.items ?? [];
  const articles = useMemo(() => articlesData?.items ?? [], [articlesData?.items]);
  const summaries = useMemo(() => summariesData?.items ?? [], [summariesData?.items]);
  const fallbackDate = summariesData?.is_fallback
    ? summariesData.date
    : articlesData?.is_fallback
      ? articlesData.date
      : null;
  const fallbackDateLabel = formatContentDate(fallbackDate);
  const showIndicatorSkeleton = isFetchingIndicators;
  const showArticleSkeleton = isFetchingArticles;
  const showSummarySkeleton = isFetchingSummaries;
  const showWeatherSkeleton = isFetchingWeather;

  const prioritizedArticles = useMemo(() => prioritizeImages(articles), [articles]);
  const prioritizedSummaries = useMemo(() => prioritizeImages(summaries), [summaries]);
  const collectedArticles = useMemo(() => prioritizedArticles.slice(0, 4), [prioritizedArticles]);
  const primarySummary = prioritizedSummaries[0];
  const secondarySummaries = prioritizedSummaries.slice(1, 5);

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
      isRefreshing: isRefreshing || isFetchingIndicators || isFetchingImpactMetrics || isTriggeringSummary,
      onRefresh: handleRefresh,
    }),
    [handleRefresh, isFetchingImpactMetrics, isFetchingIndicators, isRefreshing, isTriggeringSummary],
  );
  usePageRefreshControl(refreshControl);

  return (
    <>
      <section className="home-layout">
        <section className="content-column">
          <ImpactMetricsPanel
            data={impactMetrics}
            isError={Boolean(impactMetricsError)}
            isLoading={isFetchingImpactMetrics}
          />

          <section className="lower-grid">
            <div className="home-main-column">
              {fallbackDateLabel && (
                <p className="form-notice">
                  No hay noticias de hoy todavia. Mostrando ultimas disponibles del {fallbackDateLabel}.
                </p>
              )}
              {showSummarySkeleton ? (
                <SummaryCardSkeleton />
              ) : primarySummary ? (
                <FeaturedSummary summary={primarySummary} />
              ) : null}

              <div className="home-news-board">
                <section className="briefs-board">
                  <div className="section-label">Briefs EcoBrief</div>
                  <div className="briefs-grid">
                    {showSummarySkeleton
                      ? Array.from({ length: 4 }, (_, index) => <SummaryCardSkeleton key={index} />)
                      : secondarySummaries.map((summary) => (
                          <SummaryCard key={summary.id ?? summary.title} summary={summary} />
                        ))}
                  </div>
                  {!showSummarySkeleton && secondarySummaries.length === 0 && (
                    <section className="empty-state compact">
                      <span className="panel-title">Sin briefs disponibles</span>
                      <p>Actualiza la portada para sintetizar noticias recolectadas.</p>
                    </section>
                  )}
                </section>

                <section className="collected-board">
                  <div className="section-label">Noticias recolectadas</div>
                  <div className="collected-list">
                    {showArticleSkeleton
                      ? Array.from({ length: 4 }, (_, index) => <NewsCardSkeleton key={index} />)
                      : collectedArticles.map((article) => (
                          <NewsCard key={article.id} article={article} />
                        ))}
                  </div>
                  {!showArticleSkeleton && collectedArticles.length === 0 && (
                    <section className="empty-state compact">
                      <span className="panel-title">Sin noticias recolectadas</span>
                      <p>Presiona actualizar para recolectar noticias desde las fuentes configuradas.</p>
                    </section>
                  )}
                </section>
              </div>
            </div>

            <aside className="side-stack">
              {showWeatherSkeleton ? <PanelSkeleton /> : <WeatherPanel weather={weather} />}
              <section className="economic-side-section" aria-label="Indicadores economicos">
                <div className="section-label">Datos clave</div>
                {showIndicatorSkeleton ? <MarketSkeletons /> : <ExchangeRateCards indicators={indicators} />}
                {showIndicatorSkeleton ? <MiniIndicatorSkeletons /> : <SecondaryIndicators indicators={indicators} />}
              </section>
              <section className="departments-card" id="departamentos">
                <div className="panel-title">Departamentos</div>
                <div className="chips">
                  {departments.map((department) => (
                    <span key={department}>{department}</span>
                  ))}
                </div>
              </section>
            </aside>
          </section>
        </section>
      </section>
    </>
  );
};

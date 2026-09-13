import { useCallback, useEffect, useMemo, useRef } from "react";

import { Link } from "../app/router";
import { usePageRefreshControl } from "../app/refreshControl";
import { ImpactMetricsPanel } from "../components/impact/ImpactMetricsPanel";
import {
  IconArrowRight,
  IconBell,
  IconCheckCircle,
  IconClock,
  IconCloudSun,
  IconCoins,
  IconNews,
  IconRss,
  IconShield,
  IconTrendingUp,
  IconUsers,
} from "../components/icons/Icons";
import { ArticleImage } from "../components/news/ArticleImage";
import { CardMediaFallback, CategoryTag, FactChip, SourceTag } from "../components/news/CardParts";
import { NewsCard } from "../components/news/NewsCard";
import { SummaryCard } from "../components/news/SummaryCard";
import { MarketSkeletons, NewsCardSkeleton, SummaryCardSkeleton } from "../components/ui/Skeleton";
import { trackEvent } from "../services/analytics";
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
import {
  findByExactCode,
  findOfficialUsdIndicator,
  formatNumber,
} from "../components/indicators/indicatorUtils";
import { formatPublishedDate } from "../utils/date";
import { buildContextualSummary, cleanGeneratedText } from "../utils/summaryText";

const STEPS = [
  {
    icon: <IconRss size={20} />,
    title: "Recolecta",
    body: "Lee Radio Fides, Unitel, Red Uno, Red Bolivision, Los Tiempos y El Deber, todo el dia.",
  },
  {
    icon: <IconUsers size={20} />,
    title: "Agrupa",
    body: "Detecta cuando dos articulos de fuentes distintas cuentan el mismo hecho y los une en una historia.",
  },
  {
    icon: <IconShield size={20} />,
    title: "Verifica",
    body: "La IA resume y marca cada afirmacion: confirmada por varias fuentes, oficial, o de una sola fuente.",
  },
  {
    icon: <IconBell size={20} />,
    title: "Te llega",
    body: "Por Telegram, WhatsApp, email o la web, en la categoria y la hora que elegiste vos.",
  },
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
    timeZone: "America/La_Paz",
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
      <CardMediaFallback category={summary.category} image={summary.image} />
      <div className="featured-summary-copy">
        <div className="card-meta-row">
          <SourceTag category={summary.category} source={summary.source} />
          <div className="card-badges">
            <CategoryTag category={summary.category} />
            <span className="status-badge summarized">Resumido IA</span>
          </div>
        </div>
        <time className="published-date" dateTime={summary.published_at ?? summary.created_at ?? undefined}>
          {formatPublishedDate(summary.published_at ?? summary.created_at)}
        </time>
        <h2>{title}</h2>
        <p>{summaryText}</p>
        <FactChip fact={fact} />
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
    exclude_summarized: true,
  });
  const { data: summariesData, isFetching: isFetchingSummaries } = useGetSummariesQuery({
    fallback_to_latest: true,
    page_size: 20,
  });
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();
  const [triggerSummary, { isLoading: isTriggeringSummary }] = useTriggerSummaryMutation();

  const indicators = indicatorsData?.items ?? [];
  const officialRate = findOfficialUsdIndicator(indicators)?.value;
  const p2pBuy = findByExactCode(indicators, "binance_p2p_usdt_bob_buy")?.value;
  const p2pSell = findByExactCode(indicators, "binance_p2p_usdt_bob_sell")?.value;
  const weatherTemp = Number(weather?.current.temperature_2m);
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
  const summarizedArticleIds = useMemo(
    () => new Set(summaries.map((summary) => summary.article_id).filter((id): id is number => id != null)),
    [summaries],
  );
  const collectedArticles = useMemo(
    () => prioritizedArticles.filter((article) => !summarizedArticleIds.has(article.id)).slice(0, 2),
    [prioritizedArticles, summarizedArticleIds],
  );
  const primarySummary = prioritizedSummaries[0];
  const secondarySummaries = prioritizedSummaries.slice(1, 5);
  const heroPreviewSummaries = prioritizedSummaries.slice(0, 3);

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

  const hasTrackedBriefOpen = useRef(false);
  useEffect(() => {
    if (!hasTrackedBriefOpen.current && !showSummarySkeleton && summaries.length > 0) {
      hasTrackedBriefOpen.current = true;
      trackEvent("brief_opened", { metadata: { brief_count: summaries.length } });
    }
  }, [showSummarySkeleton, summaries.length]);

  return (
    <>
      <section className="landing-hero-band">
        <div className="landing-inner landing-hero">
          <div className="landing-hero-copy">
            <span className="landing-kicker">
              <IconNews size={16} />
              Bolivia, sin repetir la misma historia dos veces
            </span>
            <h1>
              Las noticias de Bolivia, <em>verificadas</em> y sin ruido.
            </h1>
            <p className="landing-lede">
              EcoBrief lee los principales medios bolivianos, junta las versiones de un mismo hecho en una sola
              historia, y te entrega un resumen con la fuente de cada dato a un clic.
            </p>
            <div className="landing-ctas">
              <Link className="button" href="/news">
                Ver todas las noticias
              </Link>
              <Link className="button secondary" href="/suscribirse">
                Suscribirme gratis
              </Link>
            </div>

            {impactMetrics?.has_data && (
              <div className="landing-stat-row">
                <div>
                  <strong>{formatNumber(impactMetrics.reduction_rate * 100, 0)}%</strong>
                  <span>reduccion del flujo</span>
                </div>
                <div>
                  <strong>{formatNumber(impactMetrics.estimated_pages_avoided, 0)}</strong>
                  <span>paginas evitadas hoy</span>
                </div>
                <div>
                  <strong>{formatNumber(impactMetrics.estimated_minutes_saved, 0)} min</strong>
                  <span>lectura ahorrada</span>
                </div>
              </div>
            )}
          </div>

          <div className="landing-preview-card" aria-label="Vista previa de EcoBrief">
            <div className="landing-preview-chrome">
              <span />
              <span />
              <span />
              <strong>ecobrief.bo</strong>
            </div>
            <div className="landing-preview-body">
              {showSummarySkeleton
                ? Array.from({ length: 3 }, (_, index) => <div className="landing-preview-row skeleton" key={index} />)
                : heroPreviewSummaries.map((summary) => (
                    <Link
                      className="landing-preview-row"
                      href={summary.article_id ? `/article/${summary.article_id}` : "/news"}
                      key={summary.id ?? summary.title}
                    >
                      <span className="landing-preview-tag">{summary.category}</span>
                      <span className="landing-preview-title">{cleanGeneratedText(summary.title)}</span>
                      <span className="landing-preview-badge">IA</span>
                    </Link>
                  ))}
            </div>
            <div className="landing-preview-footer">
              <span>Actualizado hace instantes</span>
              <span>{impactMetrics?.summaries ?? "--"} briefs hoy</span>
            </div>
          </div>
        </div>
      </section>

      <div className="landing-inner">
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
                      ? Array.from({ length: 2 }, (_, index) => <NewsCardSkeleton key={index} />)
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

              <section className="essential-data-section" aria-label="Datos esenciales">
                <div className="section-label">Datos esenciales</div>
                <div className="essential-data-grid">
                  {showIndicatorSkeleton || showWeatherSkeleton ? (
                    <MarketSkeletons />
                  ) : (
                    <>
                      <Link className="essential-data-card" href="/datos">
                        <div className="row-top">
                          <span className="icon-badge" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}>
                            <IconTrendingUp size={16} />
                          </span>
                          <span className="label">BCB</span>
                        </div>
                        <b>Bs {formatNumber(officialRate)}</b>
                        <span className="label">Tipo de cambio oficial</span>
                        <span className="essential-data-link">
                          Ver historico <IconArrowRight size={12} />
                        </span>
                      </Link>
                      <Link className="essential-data-card" href="/datos">
                        <div className="row-top">
                          <span className="icon-badge" style={{ background: "var(--amber-soft)", color: "var(--amber-ink)" }}>
                            <IconCoins size={16} />
                          </span>
                          <span className="label">Binance P2P</span>
                        </div>
                        <b>
                          Bs {formatNumber(p2pBuy)} / {formatNumber(p2pSell)}
                        </b>
                        <span className="label">Mejor compra / mejor venta</span>
                        <span className="essential-data-link">
                          Ver historico <IconArrowRight size={12} />
                        </span>
                      </Link>
                      <Link className="essential-data-card" href="/datos">
                        <div className="row-top">
                          <span className="icon-badge" style={{ background: "var(--sky-soft)", color: "var(--sky)" }}>
                            <IconCloudSun size={16} />
                          </span>
                          <span className="label">Clima</span>
                        </div>
                        <b>{Number.isNaN(weatherTemp) ? "--" : `${Math.round(weatherTemp)}C`}</b>
                        <span className="label">
                          {weather?.location.name ?? "La Paz"} - UV {formatNumber(weather?.today.uv_index_max, 0)}
                        </span>
                        <span className="essential-data-link">
                          Ver clima <IconArrowRight size={12} />
                        </span>
                      </Link>
                    </>
                  )}
                </div>
              </section>
            </div>
          </section>
        </section>
      </section>

      <section className="landing-section">
        <div className="section-label">Como funciona</div>
        <div className="landing-steps">
          {STEPS.map((step, index) => (
            <div className="landing-step" key={step.title}>
              <span className="landing-step-number">{index + 1}</span>
              <div className="landing-step-icon">{step.icon}</div>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section landing-trust">
        <div className="section-label">Nos auditamos a nosotros mismos</div>
        <p className="landing-trust-lede">
          La misma disciplina que aplicamos a cada noticia -verificar contra la fuente original- se la aplicamos a
          nuestros propios datos.
        </p>
        <ul className="landing-changelog">
          <li>
            <IconCheckCircle size={16} />
            Cada afirmacion de un resumen se descarta si no hay un articulo real que la respalde: no confiamos en lo
            que la IA "recuerda" o infiere.
          </li>
          <li>
            <IconCheckCircle size={16} />
            Si un proveedor de IA falla o se degrada, el sistema conmuta automaticamente a otro en vez de reintentar
            contra el mismo indefinidamente.
          </li>
          <li>
            <IconClock size={16} />
            Indicadores economicos actualizados cada 10 minutos, con historico verificable en la pagina de Datos.
          </li>
        </ul>
      </section>

      <section className="landing-cta-final">
        <h2>Recibi el resumen del dia, sin abrir diez pestanas.</h2>
        <Link className="button" href="/suscribirse">
          Suscribirme gratis
        </Link>
      </section>
      </div>
    </>
  );
};

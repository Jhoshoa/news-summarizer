import { useCallback, useMemo } from "react";

import { usePageRefreshControl } from "../app/refreshControl";
import { useRouter } from "../app/router";
import {
  findByExactCode,
  findGoldIndicator,
  findIndicator,
  findUfvIndicator,
  formatNumber,
} from "../components/indicators/indicatorUtils";
import { ArticleImage } from "../components/news/ArticleImage";
import { ArticleDetailSkeleton, PanelSkeleton } from "../components/ui/Skeleton";
import { WeatherPanel } from "../components/weather/WeatherPanel";
import {
  useGetArticleByIdQuery,
  useGetEconomicIndicatorsQuery,
  useGetSummariesQuery,
  useGetWeatherQuery,
  useRefreshEconomicIndicatorsMutation,
} from "../services/api";
import { formatPublishedDate } from "../utils/date";
import { buildContextualSummary } from "../utils/summaryText";

const getArticleIdFromPath = (pathname: string) => {
  const parts = pathname.split("/").filter(Boolean);
  const id = Number(parts[parts.length - 1]);
  return Number.isFinite(id) ? id : null;
};

const normalizeArticleText = (value?: string | null) =>
  String(value ?? "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();

const isDuplicateText = (value?: string | null, reference?: string | null) => {
  const normalizedValue = normalizeArticleText(value);
  const normalizedReference = normalizeArticleText(reference);
  if (!normalizedValue || !normalizedReference) {
    return false;
  }

  return (
    normalizedValue === normalizedReference ||
    (Math.abs(normalizedValue.length - normalizedReference.length) < 80 &&
      (normalizedValue.includes(normalizedReference) || normalizedReference.includes(normalizedValue)))
  );
};

export const ArticleDetailPage = () => {
  const { location } = useRouter();
  const articleId = getArticleIdFromPath(location.pathname);
  const { data: articleData, isFetching: isFetchingArticle } = useGetArticleByIdQuery(articleId ?? 1, {
    skip: articleId === null,
  });
  const { data: summaryData, isFetching: isFetchingSummary } = useGetSummariesQuery(
    articleId ? { article_id: articleId, page_size: 1 } : undefined,
    { skip: articleId === null },
  );
  const { data: indicatorsData, isFetching: isFetchingIndicators } = useGetEconomicIndicatorsQuery();
  const { data: weather, isFetching: isFetchingWeather } = useGetWeatherQuery();
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();

  const indicators = indicatorsData?.items ?? [];
  const article = articleData;
  const relatedSummary = summaryData?.items[0];
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
  const ufv = findUfvIndicator(indicators);
  const gold = findGoldIndicator(indicators);
  const treMn = findIndicator(indicators, ["tre", "mn"]);
  const treMe = findIndicator(indicators, ["tre", "me"]);
  const showArticleSkeleton = articleId === null || isFetchingArticle || isFetchingSummary;

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

  if (showArticleSkeleton) {
    return <ArticleDetailSkeleton />;
  }

  if (!article) {
    return (
      <section className="empty-state">
        <span className="panel-title">Noticia no disponible</span>
        <p>El articulo solicitado no existe en la base de datos o todavia no fue recolectado.</p>
      </section>
    );
  }

  const summaryText = relatedSummary
    ? buildContextualSummary(relatedSummary.summary, article.description)
    : undefined;
  const articleBody =
    article.content &&
    !isDuplicateText(article.content, relatedSummary?.summary) &&
    !isDuplicateText(article.content, article.description)
      ? article.content
      : "";
  const hasArticleImage = Boolean(article.image);

  return (
    <>
      <section className="detail-layout">
        <article className="detail-article">
          <span className="eyebrow">Detalle - {article.category}</span>
          <time className="published-date detail-date" dateTime={article.published_at}>
            {formatPublishedDate(article.published_at)}
          </time>
          <h1>{article.title}</h1>
          <div className="article-source-link">
            <span>Fuente original</span>
            <a href={article.url} rel="noreferrer" target="_blank">
              {article.source}
            </a>
          </div>

          <section className={hasArticleImage ? "article-content-layout has-image" : "article-content-layout"}>
            <div className="article-text-column">
              {summaryText ? (
                <section className="ai-summary">
                  <div className="panel-title">Resumen IA</div>
                  <p>{summaryText}</p>
                  {relatedSummary?.fact && <small>{relatedSummary.fact}</small>}
                </section>
              ) : (
                <section className="ai-summary pending-summary">
                  <div className="panel-title">Resumen IA pendiente</div>
                  <p>Esta noticia fue recolectada y conservada como fuente original, pero todavía no fue priorizada para síntesis IA.</p>
                </section>
              )}

              {articleBody && (
                <section className="article-body">
                  {articleBody.split(/\n+/).map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </section>
              )}
            </div>

            {hasArticleImage && (
              <aside className="article-media-column">
                <ArticleImage image={article.image} alt={article.title} />
              </aside>
            )}
          </section>
        </article>

        <aside className="detail-sidebar">
          {isFetchingIndicators ? (
            <>
              <PanelSkeleton />
              <PanelSkeleton />
            </>
          ) : (
            <>
              <section className="side-card">
                <div className="panel-title">Dolar hoy</div>
                <dl className="side-values">
                  <div>
                    <dt>Oficial C/V</dt>
                    <dd>
                      {formatNumber(officialBuy)} / {formatNumber(officialSell)}
                    </dd>
                  </div>
                  <div>
                    <dt>Referencial C/V</dt>
                    <dd>
                      {formatNumber(referenceBuy)} / {formatNumber(referenceSell)}
                    </dd>
                  </div>
                  <div>
                    <dt>P2P C/V</dt>
                    <dd>
                      {formatNumber(p2pBuy)} / {formatNumber(p2pSell)}
                    </dd>
                  </div>
                </dl>
              </section>

              <section className="side-card">
                <div className="panel-title">BCB clave</div>
                <dl className="side-values">
                  <div>
                    <dt>UFV</dt>
                    <dd>{formatNumber(ufv?.value, 5)}</dd>
                  </div>
                  <div>
                    <dt>Oro USD/O.T.F.</dt>
                    <dd>{formatNumber(gold?.value, 2)}</dd>
                  </div>
                  <div>
                    <dt>TRe MN / ME</dt>
                    <dd>
                      {formatNumber(treMn?.value, 2)} / {formatNumber(treMe?.value, 2)}
                    </dd>
                  </div>
                </dl>
              </section>
            </>
          )}

          {isFetchingWeather ? <PanelSkeleton /> : <WeatherPanel weather={weather} />}
        </aside>
      </section>
    </>
  );
};

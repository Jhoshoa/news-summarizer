import { useCallback, useMemo } from "react";

import { usePageRefreshControl } from "../app/refreshControl";
import { useRouter } from "../app/router";
import { ArticleImage } from "../components/news/ArticleImage";
import { WeatherPanel } from "../components/weather/WeatherPanel";
import { mockArticles } from "../data/mockNews";
import {
  useGetArticleByIdQuery,
  useGetEconomicIndicatorsQuery,
  useGetSummariesQuery,
  useGetWeatherQuery,
  useRefreshEconomicIndicatorsMutation,
} from "../services/api";
import { findByExactCode, findIndicator, formatNumber } from "../components/indicators/indicatorUtils";
import { formatPublishedDate } from "../utils/date";

const getArticleIdFromPath = (pathname: string) => {
  const parts = pathname.split("/").filter(Boolean);
  const id = Number(parts[parts.length - 1]);
  return Number.isFinite(id) ? id : null;
};

export const ArticleDetailPage = () => {
  const { location } = useRouter();
  const articleId = getArticleIdFromPath(location.pathname);
  const { data: articleData } = useGetArticleByIdQuery(articleId ?? 1, { skip: articleId === null });
  const { data: summaryData } = useGetSummariesQuery(
    articleId ? { article_id: articleId, page_size: 1 } : undefined,
    { skip: articleId === null },
  );
  const { data: indicatorsData, isFetching: isFetchingIndicators } = useGetEconomicIndicatorsQuery();
  const { data: weather } = useGetWeatherQuery();
  const [refreshIndicators, { isLoading: isRefreshing }] = useRefreshEconomicIndicatorsMutation();

  const indicators = indicatorsData?.items ?? [];
  const article = articleData ?? mockArticles.find((item) => item.id === articleId) ?? mockArticles[1];
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
  const ufv = findIndicator(indicators, ["ufv"]);
  const gold = findIndicator(indicators, ["oro"]);
  const treMn = findIndicator(indicators, ["tre", "mn"]);
  const treMe = findIndicator(indicators, ["tre", "me"]);
  const articleBody = article.content || article.description || "";
  const hasArticleImage = Boolean(article.image);

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
      <section className="detail-layout">
        <article className="detail-article">
          <span className="eyebrow">Detalle - {article.category}</span>
          <time className="published-date detail-date" dateTime={article.published_at}>
            {formatPublishedDate(article.published_at)}
          </time>
          <h1>{article.title}</h1>

          <section className={hasArticleImage ? "article-content-layout has-image" : "article-content-layout"}>
            <div className="article-text-column">
              <section className="ai-summary">
                <div className="panel-title">Resumen IA</div>
                <p>{relatedSummary?.summary || article.description || article.content}</p>
                {relatedSummary?.fact && <small>{relatedSummary.fact}</small>}
              </section>

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

          <WeatherPanel weather={weather} />
        </aside>
      </section>
    </>
  );
};

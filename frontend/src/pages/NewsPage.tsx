import { useCallback, useEffect, useMemo } from "react";

import { usePageRefreshControl } from "../app/refreshControl";
import { Link, useRouter } from "../app/router";
import { NewsCard } from "../components/news/NewsCard";
import { SummaryCard } from "../components/news/SummaryCard";
import { NewsCardSkeleton, SummaryCardSkeleton } from "../components/ui/Skeleton";
import { useGetArticlesQuery, useGetSummariesQuery, useTriggerSummaryMutation } from "../services/api";
import {
  buildNewsHref,
  getCategory,
  getCurrentPage,
  getDateValidationMessage,
  getNewsView,
  getSelectedDate,
  getTodayDate,
} from "../utils/newsRoute";

const navigateToDate = (date: string, category: string | undefined, view: "resumenes" | "recolectadas") => {
  return buildNewsHref(1, date, category, view);
};

const categoryTabs: Array<{ label: string; value?: string }> = [
  { label: "general" },
  { label: "economia", value: "economia" },
  { label: "politica", value: "politica" },
  { label: "deportes", value: "deportes" },
  { label: "tecnologia", value: "tecnologia" },
];

export const NewsPage = () => {
  const { location, navigate, replace } = useRouter();
  const page = getCurrentPage(location.search);
  const category = getCategory(location.search);
  const view = getNewsView(location.search);
  const selectedDate = getSelectedDate(location.search);
  const validationMessage = getDateValidationMessage(location.search, selectedDate);
  const articlesQuery = useGetArticlesQuery({
    page,
    page_size: 12,
    category,
    date: selectedDate,
    exclude_summarized: true,
  });
  const summariesQuery = useGetSummariesQuery({
    page,
    page_size: 12,
    category,
    date: selectedDate,
  });
  const [triggerSummary, { isLoading: isTriggeringSummary }] = useTriggerSummaryMutation();
  const activeData = view === "resumenes" ? summariesQuery.data : articlesQuery.data;
  const activeError = view === "resumenes" ? summariesQuery.error : articlesQuery.error;
  const isFetching = view === "resumenes" ? summariesQuery.isFetching : articlesQuery.isFetching;
  const articles = articlesQuery.data?.items ?? [];
  const summaries = summariesQuery.data?.items ?? [];
  const activeItems = activeData?.items ?? [];
  const totalPages = activeData?.total_pages ?? 1;
  const hasPrevious = page > 1;
  const hasNext = page < totalPages;
  const today = getTodayDate();
  const normalizedHref = buildNewsHref(page, selectedDate, category, view);
  const showNewsSkeleton = isFetching;

  useEffect(() => {
    if (`${location.pathname}${location.search}` !== normalizedHref) {
      replace(normalizedHref);
    }
  }, [location.pathname, location.search, normalizedHref, replace]);

  const handleRefresh = useCallback(() => {
    void triggerSummary({ refresh: true, time_of_day: "manual" }).unwrap().catch((error) => {
      console.error("Error actualizando noticias", error);
    });
  }, [triggerSummary]);

  const refreshControl = useMemo(
    () => ({
      isRefreshing: isFetching || isTriggeringSummary,
      onRefresh: handleRefresh,
    }),
    [handleRefresh, isFetching, isTriggeringSummary],
  );
  usePageRefreshControl(refreshControl);

  return (
    <>
      <section className="news-browser">
        <div className="browser-heading">
          <span className="eyebrow">EcoBrief Bolivia</span>
          <h1>{view === "resumenes" ? "Briefs priorizados" : "Noticias recolectadas"}</h1>
          <p>
            {view === "resumenes"
              ? "Lee noticias priorizadas y sintetizadas para reducir ruido informativo."
              : "Explora notas originales recolectadas que aun no aparecen en los briefs del dia."}
          </p>
        </div>

        <div className="news-toolbar">
          <label className="date-filter">
            <span>Fecha</span>
            <input
              aria-label="Fecha de noticias"
              max={today}
              type="date"
              value={selectedDate}
              onChange={(event) => navigate(navigateToDate(event.target.value || today, category, view))}
            />
          </label>
          <span className="news-count">
            {showNewsSkeleton
              ? "Cargando"
              : `${activeData?.total ?? 0} ${view === "resumenes" ? "briefs" : "noticias"} para ${selectedDate}`}
          </span>
        </div>

        {validationMessage && <p className="form-notice">{validationMessage}</p>}

        <div className="view-tabs" aria-label="Tipo de contenido">
          <Link
            className={view === "resumenes" ? "active" : ""}
            href={buildNewsHref(1, selectedDate, category, "resumenes")}
          >
            Briefs EcoBrief
          </Link>
          <Link
            className={view === "recolectadas" ? "active" : ""}
            href={buildNewsHref(1, selectedDate, category, "recolectadas")}
          >
            Noticias recolectadas
          </Link>
        </div>

        <div className="category-tabs" aria-label="Categorias">
          {categoryTabs.map((item) => (
            <Link
              className={item.value ? (category === item.value ? "active" : "") : !category ? "active" : ""}
              key={item.label}
              href={buildNewsHref(1, selectedDate, item.value, view)}
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="archive-list" aria-busy={showNewsSkeleton}>
          {showNewsSkeleton &&
            Array.from({ length: 6 }, (_, index) =>
              view === "resumenes" ? <SummaryCardSkeleton key={index} /> : <NewsCardSkeleton key={index} />,
            )}
          {!showNewsSkeleton &&
            view === "resumenes" &&
            summaries.map((summary) => <SummaryCard key={summary.id ?? summary.title} summary={summary} />)}
          {!showNewsSkeleton &&
            view === "recolectadas" &&
            articles.map((article) => <NewsCard key={article.id} article={article} />)}
        </div>

        {!showNewsSkeleton && activeError && (
          <section className="empty-state">
            <span className="panel-title">No se pudo cargar</span>
            <p>Revisa que el backend este disponible y vuelve a intentar.</p>
          </section>
        )}

        {!showNewsSkeleton && !activeError && activeItems.length === 0 && (
          <section className="empty-state">
            <span className="panel-title">
              {view === "resumenes" ? "Sin briefs para esta fecha" : "Sin noticias para esta fecha"}
            </span>
            <p>
              {view === "resumenes"
                ? `No hay briefs para ${selectedDate}. Puedes revisar noticias recolectadas o actualizar.`
                : `No hay articulos guardados para ${selectedDate}. Puedes actualizar o elegir otro dia.`}
            </p>
          </section>
        )}

        {!showNewsSkeleton && activeItems.length > 0 && (
          <nav className="pagination" aria-label="Paginacion">
            <Link
              className={!hasPrevious ? "disabled" : ""}
              href={buildNewsHref(page - 1, selectedDate, category, view)}
            >
              Anterior
            </Link>
            <span>
              Pagina {page} de {Math.max(totalPages, 1)}
            </span>
            <Link
              className={!hasNext ? "disabled" : ""}
              href={buildNewsHref(page + 1, selectedDate, category, view)}
            >
              Siguiente
            </Link>
          </nav>
        )}
      </section>
    </>
  );
};

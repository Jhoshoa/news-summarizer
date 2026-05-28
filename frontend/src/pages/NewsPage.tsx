import { useCallback, useEffect, useMemo } from "react";

import { usePageRefreshControl } from "../app/refreshControl";
import { Link, useRouter } from "../app/router";
import { NewsCard } from "../components/news/NewsCard";
import { useGetArticlesQuery, useTriggerSummaryMutation } from "../services/api";
import {
  buildNewsHref,
  getCategory,
  getCurrentPage,
  getDateValidationMessage,
  getSelectedDate,
  getTodayDate,
} from "../utils/newsRoute";

const navigateToDate = (date: string, category?: string) => {
  return buildNewsHref(1, date, category);
};

export const NewsPage = () => {
  const { location, navigate, replace } = useRouter();
  const page = getCurrentPage(location.search);
  const category = getCategory(location.search);
  const selectedDate = getSelectedDate(location.search);
  const validationMessage = getDateValidationMessage(location.search, selectedDate);
  const { data, error, isFetching } = useGetArticlesQuery({
    page,
    page_size: 12,
    category,
    date: selectedDate,
  });
  const [triggerSummary, { isLoading: isTriggeringSummary }] = useTriggerSummaryMutation();
  const articles = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;
  const hasPrevious = page > 1;
  const hasNext = page < totalPages;
  const today = getTodayDate();
  const normalizedHref = buildNewsHref(page, selectedDate, category);

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
          <span className="eyebrow">Archivo de noticias</span>
          <h1>Todas las noticias recolectadas</h1>
          <p>
            Explora las notas originales guardadas en la base de datos, incluyendo articulos que
            todavia no tienen resumen IA.
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
              onChange={(event) => navigate(navigateToDate(event.target.value || today, category))}
            />
          </label>
          <span className="news-count">
            {data ? `${data.total} noticias para ${selectedDate}` : "Cargando noticias"}
          </span>
        </div>

        {validationMessage && <p className="form-notice">{validationMessage}</p>}

        <div className="category-tabs" aria-label="Categorias">
          {["general", "economia", "politica", "deportes", "tecnologia"].map((item) => (
            <Link
              className={category === item ? "active" : ""}
              key={item}
              href={buildNewsHref(1, selectedDate, item)}
            >
              {item}
            </Link>
          ))}
        </div>

        <div className="archive-list" aria-busy={isFetching}>
          {articles.map((article) => (
            <NewsCard key={article.id} article={article} />
          ))}
        </div>

        {!isFetching && error && (
          <section className="empty-state">
            <span className="panel-title">No se pudo cargar</span>
            <p>Revisa que el backend este disponible y vuelve a intentar.</p>
          </section>
        )}

        {!isFetching && !error && articles.length === 0 && (
          <section className="empty-state">
            <span className="panel-title">Sin noticias para esta fecha</span>
            <p>No hay articulos guardados para {selectedDate}. Puedes actualizar o elegir otro dia.</p>
          </section>
        )}

        {articles.length > 0 && (
          <nav className="pagination" aria-label="Paginacion">
            <Link
              className={!hasPrevious ? "disabled" : ""}
              href={buildNewsHref(page - 1, selectedDate, category)}
            >
              Anterior
            </Link>
            <span>
              Pagina {page} de {Math.max(totalPages, 1)}
            </span>
            <Link
              className={!hasNext ? "disabled" : ""}
              href={buildNewsHref(page + 1, selectedDate, category)}
            >
              Siguiente
            </Link>
          </nav>
        )}
      </section>
    </>
  );
};

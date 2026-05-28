import { AppShell } from "../components/layout/AppShell";
import { NewsCard } from "../components/news/NewsCard";
import { useGetArticlesQuery, useTriggerSummaryMutation } from "../services/api";

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const getTodayDate = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const isValidDateValue = (value: string) => {
  if (!DATE_PATTERN.test(value)) {
    return false;
  }

  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return false;
  }

  return value === getDateValue(parsed);
};

const getDateValue = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const getCurrentPage = () => {
  const params = new URLSearchParams(window.location.search);
  const page = Number(params.get("page") ?? "1");
  return Number.isFinite(page) && page > 0 ? page : 1;
};

const getCategory = () => {
  const params = new URLSearchParams(window.location.search);
  return params.get("category") || undefined;
};

const getSelectedDate = () => {
  const today = getTodayDate();
  const params = new URLSearchParams(window.location.search);
  const value = params.get("date");
  if (!value || !isValidDateValue(value) || value > today) {
    return today;
  }

  return value;
};

const getDateValidationMessage = (selectedDate: string) => {
  const params = new URLSearchParams(window.location.search);
  const value = params.get("date");
  if (!value) {
    return "";
  }
  if (!isValidDateValue(value)) {
    return "La fecha de la URL no es valida. Se esta mostrando la fecha de hoy.";
  }
  if (value > getTodayDate()) {
    return "La fecha no puede ser futura. Se esta mostrando la fecha de hoy.";
  }
  if (value !== selectedDate) {
    return "Se ajusto la fecha seleccionada.";
  }
  return "";
};

const buildNewsHref = (page: number, date: string, category?: string) => {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("date", date);
  if (category) {
    params.set("category", category);
  }
  return `/news?${params.toString()}`;
};

const navigateToDate = (date: string, category?: string) => {
  window.location.href = buildNewsHref(1, date, category);
};

export const NewsPage = () => {
  const page = getCurrentPage();
  const category = getCategory();
  const selectedDate = getSelectedDate();
  const validationMessage = getDateValidationMessage(selectedDate);
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
  const handleRefresh = () => {
    void triggerSummary({ refresh: true, time_of_day: "manual" }).unwrap().catch((error) => {
      console.error("Error actualizando noticias", error);
    });
  };

  return (
    <AppShell
      compactHeader
      isRefreshing={isFetching || isTriggeringSummary}
      onRefresh={handleRefresh}
    >
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
              onChange={(event) => navigateToDate(event.target.value || today, category)}
            />
          </label>
          <span className="news-count">
            {data ? `${data.total} noticias para ${selectedDate}` : "Cargando noticias"}
          </span>
        </div>

        {validationMessage && <p className="form-notice">{validationMessage}</p>}

        <div className="category-tabs" aria-label="Categorias">
          {["general", "economia", "politica", "deportes", "tecnologia"].map((item) => (
            <a
              className={category === item ? "active" : ""}
              key={item}
              href={buildNewsHref(1, selectedDate, item)}
            >
              {item}
            </a>
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
            <a
              className={!hasPrevious ? "disabled" : ""}
              href={buildNewsHref(page - 1, selectedDate, category)}
            >
              Anterior
            </a>
            <span>
              Pagina {page} de {Math.max(totalPages, 1)}
            </span>
            <a
              className={!hasNext ? "disabled" : ""}
              href={buildNewsHref(page + 1, selectedDate, category)}
            >
              Siguiente
            </a>
          </nav>
        )}
      </section>
    </AppShell>
  );
};

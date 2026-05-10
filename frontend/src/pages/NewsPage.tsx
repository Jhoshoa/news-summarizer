import { AppShell } from "../components/layout/AppShell";
import { NewsCard } from "../components/news/NewsCard";
import { mockArticles } from "../data/mockNews";
import { useGetArticlesQuery } from "../services/api";

const getCurrentPage = () => {
  const params = new URLSearchParams(window.location.search);
  const page = Number(params.get("page") ?? "1");
  return Number.isFinite(page) && page > 0 ? page : 1;
};

const getCategory = () => {
  const params = new URLSearchParams(window.location.search);
  return params.get("category") || undefined;
};

const buildPageHref = (page: number, category?: string) => {
  const params = new URLSearchParams();
  params.set("page", String(page));
  if (category) {
    params.set("category", category);
  }
  return `/news?${params.toString()}`;
};

export const NewsPage = () => {
  const page = getCurrentPage();
  const category = getCategory();
  const { data, isFetching } = useGetArticlesQuery({ page, page_size: 12, category });
  const articles = data?.items.length ? data.items : mockArticles;
  const totalPages = data?.total_pages ?? 1;
  const hasPrevious = page > 1;
  const hasNext = page < totalPages;

  return (
    <AppShell compactHeader>
      <section className="news-browser">
        <div className="browser-heading">
          <span className="eyebrow">Archivo de noticias</span>
          <h1>Todas las noticias recolectadas</h1>
          <p>
            Explora las notas originales guardadas en la base de datos, incluyendo articulos que
            todavia no tienen resumen IA.
          </p>
        </div>

        <div className="category-tabs" aria-label="Categorias">
          {["general", "economia", "politica", "deportes", "tecnologia"].map((item) => (
            <a className={category === item ? "active" : ""} key={item} href={`/news?category=${item}`}>
              {item}
            </a>
          ))}
        </div>

        <div className="archive-list" aria-busy={isFetching}>
          {articles.map((article) => (
            <NewsCard key={article.id} article={article} />
          ))}
        </div>

        <nav className="pagination" aria-label="Paginacion">
          <a className={!hasPrevious ? "disabled" : ""} href={buildPageHref(page - 1, category)}>
            Anterior
          </a>
          <span>
            Pagina {page} de {Math.max(totalPages, 1)}
          </span>
          <a className={!hasNext ? "disabled" : ""} href={buildPageHref(page + 1, category)}>
            Siguiente
          </a>
        </nav>
      </section>
    </AppShell>
  );
};

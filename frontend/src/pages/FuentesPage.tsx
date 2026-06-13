import { SummaryCard } from "../components/news/SummaryCard";
import { SummaryCardSkeleton } from "../components/ui/Skeleton";
import { useGetSourcesQuery, useGetSummariesQuery } from "../services/api";

const SkeletonLine = ({ className = "" }: { className?: string }) => (
  <span className={`skeleton-block ${className}`} aria-hidden="true" />
);

const SourcesLoading = () => (
  <section className="impact-page" aria-label="Cargando fuentes">
    <header className="data-hero impact-hero">
      <div>
        <span className="eyebrow">Fuentes</span>
        <h1>Cargando fuentes de noticias</h1>
        <p>EcoBrief esta consultando las fuentes configuradas.</p>
      </div>
    </header>
    <section className="data-context-layout">
      <div className="data-context-main">
        <section className="data-panel skeleton-panel" aria-hidden="true">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} style={{ marginBottom: "0.75rem" }}>
              <SkeletonLine className="skeleton-line skeleton-line-sm" />
              <SkeletonLine className="skeleton-line skeleton-line-xs" />
            </div>
          ))}
        </section>
      </div>
      <aside className="data-context-sidebar" aria-label="Noticias resumidas">
          <div className="data-briefs-list">
            {Array.from({ length: 3 }, (_, index) => <SummaryCardSkeleton key={index} />)}
          </div>
        </aside>
    </section>
  </section>
);

const SourceItem = ({ name, url, enabled }: { name: string; url: string; enabled: boolean }) => {
  const hostname = new URL(url).hostname.replace("www.", "");
  return (
    <li style={{ marginBottom: "0.5rem", lineHeight: 1.6 }}>
      <strong>{name}</strong>
      {enabled ? null : <em style={{ color: "#9ca3af", fontSize: "0.875rem" }}> (inactivo)</em>}
      <br />
      <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: "#006d77", fontSize: "0.875rem" }}>
        {hostname}
      </a>
    </li>
  );
};

const SourcesSummary = () => (
  <header className="data-hero impact-hero">
    <div>
      <span className="eyebrow">Fuentes</span>
      <h1>Noticias de toda Bolivia</h1>
      <p>
        EcoBrief recolecta y resume informacion de multiples fuentes de noticias bolivianas para
        mantenerte informado con un solo vistazo.
      </p>
    </div>
  </header>
);

export const FuentesPage = () => {
  const { data, isFetching } = useGetSourcesQuery();
  const { data: summariesData, isFetching: isFetchingSummaries } = useGetSummariesQuery({
    fallback_to_latest: true, page_size: 3,
  });
  const sources = data?.items ?? [];
  const summaries = summariesData?.items ?? [];

  if (isFetching && sources.length === 0) return <SourcesLoading />;

  return (
    <section className="impact-page">
      <SourcesSummary />
      <section className="data-context-layout">
        <div className="data-context-main">
          <section className="data-panel">
            <div className="panel-heading">
              <span className="panel-title">Fuentes activas</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
              {sources.map((source) => (
                <SourceItem key={source.name} {...source} />
              ))}
            </ul>
          </section>
        </div>
        <aside className="data-context-sidebar" aria-label="Noticias resumidas">
          <div className="data-briefs-list">
            {isFetchingSummaries
              ? Array.from({ length: 3 }, (_, index) => <SummaryCardSkeleton key={index} />)
              : summaries.map((summary) => <SummaryCard key={summary.id ?? summary.title} summary={summary} />)}
          </div>
        </aside>
      </section>
    </section>
  );
};

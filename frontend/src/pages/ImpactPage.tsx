import { useMemo } from "react";

import { SummaryCard } from "../components/news/SummaryCard";
import { SummaryCardSkeleton } from "../components/ui/Skeleton";
import { useGetImpactMetricsQuery, useGetSummariesQuery } from "../services/api";
import { formatPublishedDate } from "../utils/date";
import { getImpactFormulaRows, getImpactPipelineRows } from "../utils/impact";

const numberFormatter = new Intl.NumberFormat("es-BO", {
  maximumFractionDigits: 1,
});

const formatNumber = (value: unknown) => {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberFormatter.format(numberValue) : "0";
};

const formatImpactDate = (value?: string | null) => {
  if (!value) {
    return "Sin fecha";
  }

  return formatPublishedDate(`${value}T00:00:00`);
};

const ImpactMetricCard = ({
  label,
  value,
  helper,
}: {
  helper: string;
  label: string;
  value: string;
}) => (
  <section className="data-panel impact-stat-card">
    <span className="panel-title">{label}</span>
    <strong>{value}</strong>
    <p>{helper}</p>
  </section>
);

const SkeletonLine = ({ className = "" }: { className?: string }) => (
  <span className={`skeleton-block ${className}`} aria-hidden="true" />
);

const ImpactMetricSkeleton = () => (
  <section className="data-panel impact-stat-card skeleton-panel" aria-hidden="true">
    <SkeletonLine className="skeleton-line skeleton-line-sm" />
    <SkeletonLine className="skeleton-line skeleton-line-lg" />
    <SkeletonLine className="skeleton-line skeleton-line-md" />
  </section>
);

const ImpactPanelSkeleton = ({ rows = 3 }: { rows?: number }) => (
  <section className="data-panel impact-flow-panel skeleton-panel" aria-hidden="true">
    <div className="panel-heading">
      <SkeletonLine className="skeleton-line skeleton-line-sm" />
      <SkeletonLine className="skeleton-line skeleton-line-md" />
    </div>
    <div className="impact-skeleton-list">
      {Array.from({ length: rows }, (_, index) => (
        <div className="impact-skeleton-row" key={index}>
          <SkeletonLine className="skeleton-line skeleton-line-xs" />
          <SkeletonLine className="skeleton-line" />
        </div>
      ))}
    </div>
  </section>
);

const ImpactLoading = () => (
  <section className="impact-page" aria-label="Cargando impacto digital">
    <header className="data-hero impact-hero">
      <div>
        <span className="eyebrow">Impacto digital</span>
        <h1>Calculando eficiencia informativa</h1>
        <p>EcoBrief esta consultando las metricas del pipeline.</p>
      </div>
    </header>
    <section className="data-context-layout">
      <div className="data-context-main">
        <section className="impact-stat-grid essential" aria-label="Cargando resumen de impacto">
          {Array.from({ length: 4 }, (_, index) => (
            <ImpactMetricSkeleton key={index} />
          ))}
        </section>
        <ImpactPanelSkeleton />
        <ImpactPanelSkeleton rows={4} />
        <ImpactPanelSkeleton />
      </div>
      <aside className="data-context-sidebar" aria-label="Cargando noticias resumidas">
        <div className="data-briefs-list">
          {Array.from({ length: 3 }, (_, index) => (
            <SummaryCardSkeleton key={index} />
          ))}
        </div>
      </aside>
    </section>
  </section>
);

const ImpactEmptyState = ({ isError = false }: { isError?: boolean }) => (
  <section className="impact-page">
    <header className="data-hero impact-hero">
      <div>
        <span className="eyebrow">Impacto digital</span>
        <h1>{isError ? "No se pudo cargar el impacto" : "Sin datos suficientes"}</h1>
        <p>
          {isError
            ? "Revisa que el backend este disponible y vuelve a intentar."
            : "Actualiza la portada para recolectar noticias y calcular el impacto informativo."}
        </p>
      </div>
    </header>
  </section>
);

const ImpactSummary = () => (
  <header className="data-hero impact-hero">
    <div>
      <span className="eyebrow">Impacto digital</span>
      <h1>Menos paginas abiertas, mas lectura util</h1>
      <p>
        EcoBrief recolecta, filtra y resume noticias para que el lector revise contexto local sin
        navegar repetidamente por decenas de paginas.
      </p>
    </div>
  </header>
);

export const ImpactPage = () => {
  const { data: metrics, isError, isFetching } = useGetImpactMetricsQuery({ fallback_to_latest: true });
  const { data: summariesData, isFetching: isFetchingSummaries } = useGetSummariesQuery({
    fallback_to_latest: true,
    page_size: 3,
  });
  const formulaRows = useMemo(() => getImpactFormulaRows(metrics), [metrics]);
  const pipelineRows = useMemo(() => {
    const rows = getImpactPipelineRows(metrics);
    return rows.filter((row) => ["Recolectadas", "Utiles", "Unicas", "Briefs"].includes(row.label));
  }, [metrics]);
  const summaries = summariesData?.items ?? [];

  if (isFetching && !metrics) {
    return <ImpactLoading />;
  }

  if (isError) {
    return <ImpactEmptyState isError />;
  }

  if (!metrics || !metrics.has_data) {
    return <ImpactEmptyState />;
  }

  return (
    <section className="impact-page">
      <ImpactSummary />

      {metrics.is_fallback && (
        <p className="form-notice">
          No hay metricas para {formatImpactDate(metrics.requested_date)}. Se muestran las ultimas
          disponibles del {formatImpactDate(metrics.date)}.
        </p>
      )}

      <section className="data-context-layout">
        <div className="data-context-main">
          <section className="impact-stat-grid essential" aria-label="Resumen de impacto">
            <ImpactMetricCard
              helper="Noticias tomadas como entrada para el flujo editorial."
              label="Procesadas"
              value={formatNumber(metrics.collected_articles)}
            />
            <ImpactMetricCard
              helper="Sintesis finales para lectura rapida."
              label="Briefs"
              value={formatNumber(metrics.summaries)}
            />
            <ImpactMetricCard
              helper="Paginas que el lector no necesita abrir una por una."
              label="Paginas evitadas"
              value={formatNumber(metrics.estimated_pages_avoided)}
            />
            <ImpactMetricCard
              helper="Estimacion orientativa de tiempo ahorrado."
              label="Minutos estimados"
              value={formatNumber(metrics.estimated_minutes_saved)}
            />
          </section>

          <section className="data-panel impact-flow-panel">
            <div className="panel-heading">
              <span className="panel-title">Como ayuda EcoBrief</span>
              <p>El impacto real es reducir ruido: menos busqueda manual y mas contexto comparable.</p>
            </div>
            <div className="impact-narrative-list">
              <div>
                <strong>Filtra volumen</strong>
                <p>Recolecta muchas notas, descarta lo redundante y conserva lo que aporta contexto.</p>
              </div>
              <div>
                <strong>Evita repeticion</strong>
                <p>Agrupa duplicados y notas similares para que el lector no lea lo mismo varias veces.</p>
              </div>
              <div>
                <strong>Prioriza lectura</strong>
                <p>Convierte el flujo en briefs con fuente visible para decidir que abrir y contrastar.</p>
              </div>
            </div>
          </section>

          <section className="data-panel impact-flow-panel">
            <div className="panel-heading">
              <span className="panel-title">Flujo simplificado</span>
              <p>De muchas notas a pocos briefs utiles para revisar.</p>
            </div>
            <div className="impact-flow" aria-label="Flujo de articulos procesados">
              {pipelineRows.map((item, index) => (
                <div className="impact-flow-step" key={item.label}>
                  {index > 0 && <span className="impact-flow-arrow">-&gt;</span>}
                  <div>
                    <strong>{formatNumber(item.value)}</strong>
                    <span>{item.label}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="data-panel">
            <div className="panel-heading">
              <span className="panel-title">Como se estima</span>
              <p>Indicadores de eficiencia informativa, no mediciones energeticas certificadas.</p>
            </div>
            <div className="impact-formula-list compact">
              {formulaRows.slice(0, 3).map((row) => (
                <div className="impact-formula-row" key={row.label}>
                  <span>{row.label}</span>
                  <strong>{row.value}</strong>
                  <code>{row.formula}</code>
                </div>
              ))}
            </div>
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

import { useMemo } from "react";

import { SummaryCard } from "../components/news/SummaryCard";
import { SummaryCardSkeleton } from "../components/ui/Skeleton";
import { useGetImpactMetricsQuery, useGetSummariesQuery } from "../services/api";
import { formatPublishedDate } from "../utils/date";
import { getImpactPipelineRows } from "../utils/impact";

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

const SkeletonLine = ({ className = "" }: { className?: string }) => (
  <span className={`skeleton-block ${className}`} aria-hidden="true" />
);

const PipelineDonut = ({ pct }: { pct: number }) => {
  const size = 176;
  const sw = 26;
  const r = (size - sw) / 2;
  const c = 2 * Math.PI * r;
  const briefs = Math.max(pct * c, 0);
  const gap = Math.max(c - briefs, 0);
  const briefsPct = Math.round(pct * 100);
  const removedPct = 100 - briefsPct;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="#9ca3af" strokeWidth={sw} />
        <circle cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="#16a34a" strokeWidth={sw}
          strokeDasharray={`${briefs} ${gap}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dasharray 0.6s ease" }} />
        <text x={size / 2} y={size / 2 - 4} textAnchor="middle"
          fontSize="22" fontWeight="700" fill="#111827">
          {removedPct}%
        </text>
        <text x={size / 2} y={size / 2 + 12} textAnchor="middle"
          fontSize="11" fill="#6b7280">descartadas</text>
      </svg>
      <div style={{ display: "flex", gap: "1rem", fontSize: "0.8rem" }}>
        <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", backgroundColor: "#9ca3af", marginRight: 4 }} /> {removedPct}%</span>
        <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", backgroundColor: "#16a34a", marginRight: 4 }} /> {briefsPct}%</span>
      </div>
    </div>
  );
};

const PIPELINE_COLORS = ["#6b7280", "#d97706", "#006d77", "#16a34a"];

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
          <section className="data-panel impact-flow-panel">
            <div className="panel-heading">
              <span className="panel-title">Flujo del pipeline</span>
              <p>De {formatNumber(metrics.collected_articles)} noticias recolectadas a {formatNumber(metrics.summaries)} briefs.</p>
            </div>
            <div className="pipeline-layout" style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start", flexWrap: "wrap" }}>
              <div className="pipeline-donut">
                <PipelineDonut pct={metrics.collected_articles > 0 ? metrics.summaries / metrics.collected_articles : 0} />
              </div>
              <div className="pipeline-steps-vertical">
                {pipelineRows.map((row, i) => {
                  const total = metrics.collected_articles;
                  const pctStr = total > 0 ? `${((row.value / total) * 100).toFixed(0)}%` : "—";
                  return (
                    <div key={row.label} className="pipeline-step-row"
                      style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.625rem" }}>
                      <span style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: PIPELINE_COLORS[i % PIPELINE_COLORS.length], flexShrink: 0 }} />
                      <span style={{ fontSize: "0.9rem", color: "#374151" }}>{row.label}</span>
                      <span style={{ fontSize: "0.8rem", color: "#6b7280", marginLeft: "auto" }}>{pctStr}</span>
                      <strong style={{ fontSize: "1rem", minWidth: "2.5rem", textAlign: "right" }}>{formatNumber(row.value)}</strong>
                    </div>
                  );
                })}
              </div>
              <div className="pipeline-formulas" style={{ fontSize: "0.8rem", lineHeight: 1.5, color: "#374151", minWidth: "11rem" }}>
                <div style={{ marginBottom: "0.9rem" }}>
                  <strong style={{ fontSize: "0.85rem" }}>Paginas evitadas</strong>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <div>
                      <div>{formatNumber(metrics.collected_articles)} − {formatNumber(metrics.summaries)} = {formatNumber(metrics.estimated_pages_avoided)}</div>
                      <code style={{ fontSize: "0.75rem", color: "#6b7280" }}>recolectadas − briefs</code>
                    </div>
                    <strong style={{ fontSize: "1.5rem", color: "#006d77", whiteSpace: "nowrap" }}>
                      {formatNumber(metrics.estimated_pages_avoided)} paginas evitadas
                    </strong>
                  </div>
                </div>
                <div style={{ marginBottom: "0.9rem" }}>
                  <strong style={{ fontSize: "0.85rem" }}>Reduccion estimada</strong>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <div>
                      <div>1 − {formatNumber(metrics.summaries)} / {formatNumber(metrics.collected_articles)} = {formatNumber(metrics.reduction_rate * 100)}%</div>
                      <code style={{ fontSize: "0.75rem", color: "#6b7280" }}>1 − briefs / recolectadas</code>
                    </div>
                    <strong style={{ fontSize: "1.5rem", color: "#006d77", whiteSpace: "nowrap" }}>
                      {formatNumber(metrics.reduction_rate * 100)}% paginas descartadas
                    </strong>
                  </div>
                </div>
                <div>
                  <strong style={{ fontSize: "0.85rem" }}>Minutos estimados</strong>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <div>
                      <div>{formatNumber(metrics.estimated_pages_avoided)} × 0.5 <span style={{ color: "#6b7280" }}>(30s c/u)</span> = {formatNumber(metrics.estimated_minutes_saved)}</div>
                      <code style={{ fontSize: "0.75rem", color: "#6b7280" }}>paginas evitadas × 30s</code>
                    </div>
                    <strong style={{ fontSize: "1.5rem", color: "#006d77", whiteSpace: "nowrap" }}>
                      {formatNumber(metrics.estimated_minutes_saved)} min de lectura evitada
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="data-panel">
            <div className="panel-heading">
              <span className="panel-title">Como se priorizan las noticias</span>
              <p>Cada noticia recibe un puntaje segun estos criterios. Las mejor puntuadas pasan al resumen.</p>
            </div>
            <div className="scoring-layout" style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
              <div className="scoring-bars" style={{ flex: "0 0 auto", minWidth: "14rem" }}>
                {[
                  { label: "Actualidad", pct: 15 },
                  { label: "Relevancia local", pct: 20 },
                  { label: "Impacto informativo", pct: 20 },
                  { label: "Calidad contenido", pct: 17 },
                  { label: "Fuente", pct: 10 },
                  { label: "Corroboracion", pct: 10 },
                  { label: "Confianza categoria", pct: 8 },
                ].map((c) => (
                  <div key={c.label} style={{ marginBottom: "0.4rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "0.15rem" }}>
                      <span style={{ color: "#374151" }}>{c.label}</span>
                      <span style={{ color: "#6b7280" }}>{c.pct}%</span>
                    </div>
                    <div style={{ height: 8, backgroundColor: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ width: `${c.pct}%`, height: "100%", backgroundColor: "#006d77", borderRadius: 4, transition: "width 0.5s ease" }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="impact-narrative-list" style={{ flex: 1, minWidth: "16rem" }}>
                <div>
                  <strong>Actualidad (15%)</strong>
                  <p>Noticias mas recientes reciben mayor puntaje. Dentro de las ultimas horas pesa mas.</p>
                </div>
                <div>
                  <strong>Relevancia local (20%)</strong>
                  <p>Mencion de regiones, ciudades o autoridades de Bolivia.</p>
                </div>
                <div>
                  <strong>Impacto informativo (20%)</strong>
                  <p>Palabras clave sobre economia, politica, salud, educacion y seguridad.</p>
                </div>
                <div>
                  <strong>Calidad del contenido (17%)</strong>
                  <p>Noticias con mayor extension, imagenes y descripcion clara.</p>
                </div>
                <div>
                  <strong>Fuente (10%)</strong>
                  <p>Fuentes reconocidas de noticias bolivianas tienen mayor peso inicial.</p>
                </div>
                <div>
                  <strong>Corroboracion (10%)</strong>
                  <p>Noticias cubiertas por multiples fuentes suman puntos adicionales.</p>
                </div>
                <div>
                  <strong>Confianza de categoria (8%)</strong>
                  <p>Que tan coherente es el contenido con la categoria asignada.</p>
                </div>
              </div>
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

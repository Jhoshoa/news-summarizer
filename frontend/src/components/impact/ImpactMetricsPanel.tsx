import { useCallback, useEffect, useRef, useState } from "react";
import type { ImpactMetricsResponse } from "../../services/types";

type ImpactMetricsPanelProps = {
  data?: ImpactMetricsResponse;
  isError?: boolean;
  isLoading?: boolean;
};

const numberFormatter = new Intl.NumberFormat("es-BO", {
  maximumFractionDigits: 1,
});

const percentFormatter = new Intl.NumberFormat("es-BO", {
  maximumFractionDigits: 0,
  style: "percent",
});

const formatNumber = (value: unknown) => {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberFormatter.format(numberValue) : "0";
};

const formatPercent = (value: unknown) => {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? percentFormatter.format(numberValue) : "0%";
};

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

export const ImpactMetricsPanel = ({ data, isError = false, isLoading = false }: ImpactMetricsPanelProps) => {
  const [runsOpen, setRunsOpen] = useState(false);
  const runsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRunsTimer = useCallback(() => {
    if (runsTimerRef.current) {
      clearTimeout(runsTimerRef.current);
      runsTimerRef.current = null;
    }
  }, []);

  const openRuns = useCallback(() => {
    setRunsOpen(true);
    runsTimerRef.current = setTimeout(() => setRunsOpen(false), 30000);
  }, []);

  const closeRuns = useCallback(() => {
    setRunsOpen(false);
    clearRunsTimer();
  }, [clearRunsTimer]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeRuns();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [closeRuns]);

  useEffect(() => () => clearRunsTimer(), [clearRunsTimer]);

  if (isLoading) {
    return (
      <section className="impact-panel skeleton-panel" aria-label="Cargando impacto digital">
        <div className="impact-compact-row">
          <span className="skeleton-block skeleton-line skeleton-line-md" />
          <span className="skeleton-block skeleton-line skeleton-line-lg" />
        </div>
        <div className="impact-compact-row">
          <span className="skeleton-block skeleton-line" />
        </div>
      </section>
    );
  }

  if (isError) {
    return (
      <section className="impact-panel">
        <div className="impact-heading">
          <span className="section-label">Impacto digital</span>
          <h2>No se pudo cargar el impacto informativo</h2>
        </div>
        <p className="impact-note">Revisa que el backend este disponible y vuelve a intentar.</p>
      </section>
    );
  }

  if (!data || !data.has_data) {
    return (
      <section className="impact-panel">
        <div className="impact-heading">
          <span className="section-label">Impacto digital</span>
          <h2>Actualiza la portada para calcular el impacto de hoy</h2>
        </div>
        <p className="impact-note">
          EcoBrief mostrara aqui articulos procesados, briefs generados y estimaciones de navegacion evitada.
        </p>
      </section>
    );
  }

  const effectiveDate = formatContentDate(data.date);
  const requestedDate = formatContentDate(data.requested_date);
  const hasPipelineMetrics = data.data_source === "pipeline_run";
  const flowLabel = hasPipelineMetrics ? "Flujo real (ultima corrida)" : "Flujo estimado";
  const lastRun = hasPipelineMetrics && data.runs && data.runs.length > 0 ? data.runs[data.runs.length - 1] : null;
  const existingArticles = lastRun ? (lastRun.updated_count ?? 0) : 0;
  const cumulativeBriefs = lastRun ? lastRun.pipeline.find(s => s.label === "Briefs")?.value ?? data.summaries : data.summaries;
  const flowParts = hasPipelineMetrics && lastRun
    ? [
        { label: "recolectadas", value: lastRun.pipeline[0]?.value ?? data.collected_articles },
        { label: "utiles", value: lastRun.pipeline[1]?.value ?? data.usable_articles },
        { label: "unicas", value: lastRun.pipeline[2]?.value ?? data.unique_articles },
        { label: "candidatas", value: lastRun.pipeline[3]?.value ?? data.summary_candidates ?? 0 },
        { label: "briefs", value: lastRun.briefs_count ?? lastRun.pipeline[4]?.value ?? data.summaries },
      ]
    : data.pipeline.map((item) => ({
        label: item.label.toLowerCase(),
        value: item.value,
      }));

  return (
    <section className="impact-panel">
      <div className="impact-compact-row impact-main-row">
        <div className="impact-title-group">
          <span className="section-label">Impacto digital</span>
          <strong>{effectiveDate}</strong>
        </div>
        <div className="impact-metric-strip">
          <span>
            <b>{formatNumber(data.collected_articles)}</b> procesadas
          </span>
          <span>
            <b>{formatNumber(data.summaries)}</b> briefs
          </span>
          <span>
            <b>{formatNumber(data.estimated_pages_avoided)}</b> paginas evitadas
          </span>
          <span>
            <b>{formatNumber(data.estimated_minutes_saved)}</b> min estimados
          </span>
        </div>
      </div>

      <div className="impact-compact-row impact-detail-row">
        <p>
          {flowLabel}:{" "}
          {flowParts.map((item, index) => (
            <span key={item.label}>
              {index > 0 && " -> "}
              <b>{formatNumber(item.value)}</b> {item.label}
              {item.label === "unicas" && existingArticles > 0 && (
                <span className="impact-run-acumulado"> ({formatNumber(existingArticles)} existentes)</span>
              )}
              {item.label === "briefs" && lastRun && lastRun.briefs_count != null && cumulativeBriefs !== lastRun.briefs_count && (
                <span className="impact-run-acumulado"> ({formatNumber(cumulativeBriefs)} acum)</span>
              )}
            </span>
          ))}
          {" · "}reduccion estimada: <b>{formatPercent(data.reduction_rate)}</b>.
        </p>
        <small>{data.methodology.note}</small>
        {data.runs && data.runs.length > 0 && (
            <button className="impact-runs-trigger" onClick={() => (runsOpen ? closeRuns() : openRuns())} type="button">
              {" "}{runsOpen ? "▴" : "▾"} {runsOpen ? "Ocultar detalle" : "Ver detalle"}
            </button>
          )}
      </div>

      {data.runs && data.runs.length > 0 && (
        <>
          {runsOpen && <div className="impact-runs-backdrop" onClick={closeRuns} />}

          <div
            className={`impact-runs-overlay ${runsOpen ? "impact-runs-overlay--open" : ""}`}
            aria-hidden={!runsOpen}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="impact-runs-overlay-header">
              <span className="impact-runs-overlay-title">Corridas del dia</span>
              <button className="impact-runs-overlay-close" onClick={closeRuns} type="button" aria-label="Cerrar detalle">
                ▴
              </button>
            </div>
            <div className="impact-runs-overlay-body">
              {data.runs.map((run) => (
                <div className="impact-run-row" key={run.started_at ?? run.time}>
                  <span className="impact-run-time">{run.time}</span>
                  <span className="impact-run-pipeline">
                    {run.pipeline.map((step, index) => (
                      <span key={step.label}>
                        {index > 0 && " → "}
                        {step.label === "Briefs" && run.briefs_count != null ? (
                          <><b>{formatNumber(run.briefs_count)}</b> {step.label.toLowerCase()} <span className="impact-run-acumulado">({formatNumber(step.value)} acum)</span></>
                        ) : step.label === "Unicas" && run.updated_count != null && run.updated_count > 0 ? (
                          <><b>{formatNumber(step.value)}</b> {step.label.toLowerCase()} <span className="impact-run-acumulado">({formatNumber(run.updated_count)} existentes)</span></>
                        ) : (
                          <><b>{formatNumber(step.value)}</b> {step.label.toLowerCase()}</>
                        )}
                      </span>
                    ))}
                  </span>
                  {run.cache_reused && <span className="impact-run-cache">cache</span>}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {data.is_fallback && requestedDate && (
        <div className="impact-compact-row">
          <p className="form-notice">
            No hay metricas para {requestedDate}. Mostrando ultimas disponibles del {effectiveDate}.
          </p>
        </div>
      )}
    </section>
  );
};

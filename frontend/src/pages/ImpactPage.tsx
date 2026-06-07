import { useMemo } from "react";

import { useGetImpactMetricsQuery } from "../services/api";
import type { ImpactMetricsResponse } from "../services/types";
import { formatPublishedDate } from "../utils/date";
import {
  getImpactDataSourceLabel,
  getImpactDataSourceTone,
  getImpactFormulaRows,
  getImpactPipelineRows,
} from "../utils/impact";

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

const ImpactLoading = () => (
  <section className="impact-page" aria-label="Cargando impacto digital">
    <header className="data-hero impact-hero">
      <div>
        <span className="eyebrow">Impacto digital</span>
        <h1>Calculando eficiencia informativa</h1>
        <p>EcoBrief esta consultando las metricas del pipeline.</p>
      </div>
      <div className="data-status-card">
        <span className="skeleton-block skeleton-line skeleton-line-md" aria-hidden="true" />
        <span className="skeleton-block skeleton-line skeleton-line-lg" aria-hidden="true" />
      </div>
    </header>
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
      <div className="data-status-card">
        <span>Fuente de datos</span>
        <strong>{isError ? "Error de consulta" : "Sin datos"}</strong>
        <small>No se muestran estimaciones ambientales exactas.</small>
      </div>
    </header>
  </section>
);

const ImpactSummary = ({ metrics }: { metrics: ImpactMetricsResponse }) => {
  const dataSourceTone = getImpactDataSourceTone(metrics.data_source);
  const dataSourceLabel = getImpactDataSourceLabel(metrics.data_source);

  return (
    <header className="data-hero impact-hero">
      <div>
        <span className="eyebrow">Impacto digital</span>
        <h1>Como EcoBrief reduce navegacion repetida</h1>
        <p>
          La pagina muestra el flujo informativo del dia, las estimaciones usadas y los limites de
          la metodologia Green Tech del proyecto.
        </p>
      </div>
      <div className={`data-status-card impact-source-card ${dataSourceTone}`}>
        <span>Fecha analizada</span>
        <strong>{formatImpactDate(metrics.date)}</strong>
        <small>{dataSourceLabel}</small>
      </div>
    </header>
  );
};

export const ImpactPage = () => {
  const { data: metrics, isError, isFetching } = useGetImpactMetricsQuery({ fallback_to_latest: true });
  const formulaRows = useMemo(() => getImpactFormulaRows(metrics), [metrics]);
  const pipelineRows = useMemo(() => getImpactPipelineRows(metrics), [metrics]);

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
      <ImpactSummary metrics={metrics} />

      {metrics.is_fallback && (
        <p className="form-notice">
          No hay metricas para {formatImpactDate(metrics.requested_date)}. Se muestran las ultimas
          disponibles del {formatImpactDate(metrics.date)}.
        </p>
      )}

      <section className="impact-stat-grid" aria-label="Resumen de impacto">
        <ImpactMetricCard
          helper="Articulos que entraron al flujo de EcoBrief."
          label="Procesadas"
          value={formatNumber(metrics.collected_articles)}
        />
        <ImpactMetricCard
          helper="Sintesis finales generadas para lectura rapida."
          label="Briefs"
          value={formatNumber(metrics.summaries)}
        />
        <ImpactMetricCard
          helper="Paginas que el usuario no necesita revisar una por una."
          label="Paginas evitadas"
          value={formatNumber(metrics.estimated_pages_avoided)}
        />
        <ImpactMetricCard
          helper="Tiempo orientativo con 0.5 min por pagina evitada."
          label="Minutos estimados"
          value={formatNumber(metrics.estimated_minutes_saved)}
        />
        <ImpactMetricCard
          helper="Transferencia evitada estimada con 0.8 MB por pagina."
          label="Datos estimados"
          value={`${formatNumber(metrics.estimated_data_saved_mb)} MB`}
        />
        <ImpactMetricCard
          helper="Relacion entre briefs finales y articulos recolectados."
          label="Reduccion"
          value={formatPercent(metrics.reduction_rate)}
        />
      </section>

      <section className="data-panel wide-panel impact-flow-panel">
        <div className="panel-heading">
          <span className="panel-title">Flujo del pipeline</span>
          <p>EcoBrief filtra, deduplica y prioriza antes de resumir con IA.</p>
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
        <div className="metric-list">
          <div>
            <span>Descartadas por calidad</span>
            <strong>{formatNumber(metrics.quality_dropped_articles ?? 0)}</strong>
          </div>
          <div>
            <span>Duplicadas evitadas</span>
            <strong>{formatNumber(metrics.duplicate_articles ?? metrics.duplicate_articles_estimated)}</strong>
          </div>
          <div>
            <span>Rankeadas</span>
            <strong>{formatNumber(metrics.ranked_articles ?? metrics.unique_articles)}</strong>
          </div>
          <div>
            <span>Llamadas IA evitadas estimadas</span>
            <strong>{formatNumber(metrics.ai_calls_avoided_estimated)}</strong>
          </div>
          <div>
            <span>Cache reutilizado</span>
            <strong>{metrics.cache_reused ? "Si" : "No"}</strong>
          </div>
        </div>
      </section>

      <section className="data-grid">
        <section className="data-panel wide-panel">
          <div className="panel-heading">
            <span className="panel-title">Metodologia</span>
            <p>Los calculos son indicadores de eficiencia informativa, no mediciones energeticas.</p>
          </div>
          <div className="impact-formula-list">
            {formulaRows.map((row) => (
              <div className="impact-formula-row" key={row.label}>
                <span>{row.label}</span>
                <code>{row.formula}</code>
                <strong>{row.value}</strong>
              </div>
            ))}
          </div>
          <p className="impact-disclaimer">
            {metrics.methodology.note} No se reportan CO2, kWh ni impacto ambiental certificado
            porque no hay medicion directa.
          </p>
        </section>
      </section>

      <section className="data-grid" id="fuentes">
        <section className="data-panel">
          <span className="panel-title">Fuentes monitoreadas</span>
          <p className="impact-section-copy">
            EcoBrief conserva fuentes visibles y enlaces originales en cada noticia o brief. Un
            estado tecnico por fuente debe salir de datos reales o de un endpoint dedicado.
          </p>
        </section>
        <section className="data-panel">
          <span className="panel-title">Uso responsable de IA</span>
          <p className="impact-section-copy">
            El sistema filtra calidad, deduplica, rankea y selecciona candidatas antes de resumir.
            Asi evita procesar contenido redundante cuando el pipeline tiene datos suficientes.
          </p>
        </section>
        <section className="data-panel" id="politica-editorial">
          <span className="panel-title">Politica editorial</span>
          <p className="impact-section-copy">
            EcoBrief no reemplaza a los medios ni produce reporterias propias. Resume y organiza
            noticias existentes, mantiene la fuente visible y reconoce que los resumenes automaticos
            deben contrastarse con el enlace original.
          </p>
        </section>
      </section>
    </section>
  );
};

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
  const flowLabel = hasPipelineMetrics ? "Flujo real" : "Flujo estimado";
  const flowParts = hasPipelineMetrics
    ? [
        { label: "recolectadas", value: data.collected_articles },
        { label: "utiles", value: data.usable_articles },
        { label: "unicas", value: data.unique_articles },
        { label: "briefs", value: data.summaries },
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
            </span>
          ))}
          {" · "}reduccion estimada: <b>{formatPercent(data.reduction_rate)}</b>.
        </p>
        <small>{data.methodology.note}</small>
      </div>

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

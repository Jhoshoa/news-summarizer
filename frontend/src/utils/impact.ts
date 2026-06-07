import type { ImpactMetricsResponse } from "../services/types";

export type ImpactDataSource = NonNullable<ImpactMetricsResponse["data_source"]>;

export const getImpactDataSourceLabel = (dataSource?: ImpactMetricsResponse["data_source"]) => {
  if (dataSource === "pipeline_run") {
    return "Fuente de datos: corrida real del pipeline.";
  }

  if (dataSource === "derived") {
    return "Fuente de datos: estimacion derivada de articulos y briefs guardados.";
  }

  return "Sin datos suficientes para calcular impacto.";
};

export const getImpactDataSourceTone = (
  dataSource?: ImpactMetricsResponse["data_source"],
): "strong" | "muted" | "empty" => {
  if (dataSource === "pipeline_run") {
    return "strong";
  }

  if (dataSource === "derived") {
    return "muted";
  }

  return "empty";
};

export const getImpactFormulaRows = (metrics?: ImpactMetricsResponse) => {
  const minutesPerArticle = metrics?.methodology.minutes_per_article ?? 0.5;
  const mbPerPage = metrics?.methodology.mb_per_page ?? 0.8;

  return [
    {
      label: "Paginas evitadas",
      formula: "recolectadas - briefs",
      value:
        metrics && metrics.has_data
          ? `${metrics.collected_articles} - ${metrics.summaries} = ${metrics.estimated_pages_avoided}`
          : "sin datos",
    },
    {
      label: "Reduccion estimada",
      formula: "1 - briefs / recolectadas",
      value:
        metrics && metrics.has_data && metrics.collected_articles > 0
          ? `1 - ${metrics.summaries} / ${metrics.collected_articles}`
          : "sin datos",
    },
    {
      label: "Minutos estimados",
      formula: `paginas evitadas * ${minutesPerArticle}`,
      value:
        metrics && metrics.has_data
          ? `${metrics.estimated_pages_avoided} * ${minutesPerArticle} = ${metrics.estimated_minutes_saved}`
          : "sin datos",
    },
    {
      label: "Datos estimados",
      formula: `paginas evitadas * ${mbPerPage} MB`,
      value:
        metrics && metrics.has_data
          ? `${metrics.estimated_pages_avoided} * ${mbPerPage} = ${metrics.estimated_data_saved_mb} MB`
          : "sin datos",
    },
  ];
};

export const getImpactPipelineRows = (metrics?: ImpactMetricsResponse) => {
  if (!metrics || !metrics.has_data) {
    return [
      { label: "Recolectadas", value: 0 },
      { label: "Utiles", value: 0 },
      { label: "Unicas", value: 0 },
      { label: "Candidatas", value: 0 },
      { label: "Briefs", value: 0 },
    ];
  }

  return [
    { label: "Recolectadas", value: metrics.collected_articles },
    { label: "Utiles", value: metrics.usable_articles ?? metrics.unique_articles },
    { label: "Unicas", value: metrics.unique_articles },
    { label: "Candidatas", value: metrics.summary_candidates ?? metrics.summaries },
    { label: "Briefs", value: metrics.summaries },
  ];
};

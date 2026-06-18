import { useMemo } from "react";

import { SummaryCard } from "../components/news/SummaryCard";
import { SummaryCardSkeleton } from "../components/ui/Skeleton";
import { useGetImpactMetricsQuery, useGetSummariesQuery } from "../services/api";
import type { ImpactMetricsResponse } from "../services/types";
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
  const size = 144;
  const sw = 22;
  const r = (size - sw) / 2;
  const c = 2 * Math.PI * r;
  const briefs = Math.max(pct * c, 0);
  const gap = Math.max(c - briefs, 0);
  const briefsPct = Math.round(pct * 100);
  const removedPct = 100 - briefsPct;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.4rem" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="#e5e7eb" strokeWidth={sw} />
        {briefs > 0 && (
          <circle cx={size / 2} cy={size / 2} r={r}
            fill="none" stroke="#16a34a" strokeWidth={sw}
            strokeDasharray={`${briefs} ${gap}`}
            strokeLinecap="round"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
            style={{ transition: "stroke-dasharray 0.6s ease" }} />
        )}
        <text x={size / 2} y={size / 2 - 4} textAnchor="middle"
          fontSize="20" fontWeight="700" fill="#111827">
          {removedPct}%
        </text>
        <text x={size / 2} y={size / 2 + 12} textAnchor="middle"
          fontSize="10" fill="#6b7280">descartadas</text>
      </svg>
      <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem" }}>
        <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", backgroundColor: "#e5e7eb", marginRight: 4 }} /> {removedPct}%</span>
        <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", backgroundColor: "#16a34a", marginRight: 4 }} /> {briefsPct}%</span>
      </div>
    </div>
  );
};

const PIPELINE_COLORS = ["#6b7280", "#d97706", "#006d77", "#16a34a"];

const breakText = (text: string, maxLen: number): string[] => {
  if (text.length <= maxLen) return [text];
  const lines: string[] = [];
  let remaining = text;
  while (remaining.length > 0) {
    if (remaining.length <= maxLen) { lines.push(remaining); break; }
    let cut = remaining.lastIndexOf(" ", maxLen);
    if (cut === -1) cut = maxLen;
    lines.push(remaining.slice(0, cut));
    remaining = remaining.slice(cut).trimStart();
  }
  return lines;
};

type StageDef = { label: string; count: number; color: string; icon: string };
type DropDef = { fromIdx: number; count: number; label: string };

const DESC = {
  Recolectadas: "Artículos de scrapers + NewsAPI de 6 fuentes bolivianas (Unitel, RedUno, El Deber, Los Tiempos, Red Bolivisión, Radio Fides)",
  Útiles: "Filtro de calidad: se descartan artículos sin título, sin imagen o con contenido insuficiente",
  Únicas: "Artículos nuevos insertados en base de datos (no existían previamente)",
  Candidatas: "Selección diversa por categoría para generar resúmenes (top 5 por categoría, máx 2 por fuente)",
  Briefs: "",
};

const PipelineFlowSVG = ({ metrics }: { metrics: ImpactMetricsResponse }) => {
  const isPipelineRun = metrics.data_source === "pipeline_run";
  const lastRun = isPipelineRun && metrics.runs && metrics.runs.length > 0
    ? metrics.runs[metrics.runs.length - 1]
    : null;

  const total = lastRun ? (lastRun.pipeline[0]?.value ?? metrics.collected_articles) : metrics.collected_articles;
  const fmt = (n: number) => formatNumber(n);
  const pctStr = (n: number) => (total > 0 ? `${((n / total) * 100).toFixed(0)}%` : "—");
  const modelLabel = metrics.llm_model && metrics.llm_provider
    ? `Generados con ${metrics.llm_model} vía ${metrics.llm_provider}`
    : "Resumidos con IA (Groq)";

  const usable = lastRun ? (lastRun.pipeline[1]?.value ?? metrics.usable_articles ?? 0) : (metrics.usable_articles ?? 0);
  const unicas = lastRun ? (lastRun.inserted_count ?? lastRun.pipeline[2]?.value ?? metrics.unique_articles) : metrics.unique_articles;
  const candidatas = lastRun ? (lastRun.pipeline[3]?.value ?? metrics.summary_candidates ?? 0) : (metrics.summary_candidates ?? 0);
  const ranked = lastRun ? (metrics.ranked_articles ?? 0) : (metrics.ranked_articles ?? 0);
  const lastRunBriefs = lastRun ? (lastRun.briefs_count ?? metrics.summaries) : metrics.summaries;
  const summaries = lastRun ? lastRunBriefs : metrics.summaries;

  const stages: StageDef[] = [
    { label: "Recolectadas", count: total, color: "#6b7280", icon: "📥" },
  ];

  if (usable > 0 && usable !== total) {
    stages.push({ label: "Útiles", count: usable, color: "#d97706", icon: "🔍" });
  }

  stages.push({ label: "Únicas", count: unicas, color: "#006d77", icon: "🧹" });

  if (ranked > 0) {
    stages.push({ label: "Rankeadas", count: ranked, color: "#16a34a", icon: "⭐" });
  }

  if (candidatas > 0 && candidatas !== (stages[stages.length - 1]?.count ?? 0)) {
    stages.push({ label: "Candidatas", count: candidatas, color: "#7c3aed", icon: "📋" });
  }

  if (summaries > 0 && summaries !== (stages[stages.length - 1]?.count ?? 0)) {
    stages.push({ label: "Briefs", count: summaries, color: "#16a34a", icon: "✍️" });
  }

  const prevCount = stages[stages.length - 1]?.count ?? 0;
  const accumulated = summaries > prevCount && prevCount > 0;

  const drops: DropDef[] = [];
  for (let i = 0; i < stages.length - 1; i++) {
    const diff = stages[i].count - stages[i + 1].count;
    if (diff <= 0) continue;
    let label = "descartadas";
    if (i === 0) label = "baja calidad";
    else if (i === 1 && stages[i].label === "Útiles") label = "duplicados";
    else if (stages[i].label === "Únicas" && stages[i + 1].label === "Rankeadas") label = "no priorizadas";
    else if (stages[i].label === "Rankeadas" && stages[i + 1].label === "Candidatas") label = "no candidatas";
    else if (stages[i + 1].label === "Briefs") label = "no resumidas";
    drops.push({ fromIdx: i, count: diff, label });
  }

  const boxW = 260;
  const boxH = 48;
  const gap = 32;
  const dropW = 120;
  const dropH = 36;
  const padX = 16;
  const mainX = padX;
  const dropX = mainX + boxW + 20;
  const descX = dropX + dropW + 24;
  const svgW = 740;
  const svgH = padX + stages.length * (boxH + gap);

  return (
    <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} style={{ maxWidth: svgW, display: "block" }}>
      <defs>
        <marker id="a" markerWidth="7" markerHeight="7" refX="3.5" refY="3.5" orient="auto">
          <path d="M0,0 L7,3.5 L0,7 Z" fill="#9ca3af" />
        </marker>
        <marker id="ad" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#f87171" />
        </marker>
      </defs>

      <line x1={descX - 12} y1={padX} x2={descX - 12} y2={svgH - padX}
        stroke="#e5e7eb" strokeWidth={1} />

      {stages.map((st, i) => {
        const y0 = padX + i * (boxH + gap);
        const desc = st.label === "Briefs" ? modelLabel : DESC[st.label as keyof typeof DESC] ?? "";
        const descLines = desc ? breakText(desc, 38) : [];
        return (
          <g key={st.label}>
            <rect x={mainX} y={y0} width={boxW} height={boxH} rx={10}
              fill={st.color} fillOpacity={0.1} stroke={st.color} strokeWidth={1.5} />
            <text x={mainX + 14} y={y0 + boxH / 2 + 5} textAnchor="middle" fontSize={14}>
              {st.icon}
            </text>
            <text x={mainX + 30} y={y0 + boxH / 2 + 5} textAnchor="start"
              fontSize={12} fontWeight={600} fill="#1f2937">
              {st.label}
            </text>
            <text x={mainX + boxW - 10} y={y0 + boxH / 2 - 4} textAnchor="end"
              fontSize={16} fontWeight={700} fill={st.color}>
              {fmt(st.count)}
            </text>
            <text x={mainX + boxW - 10} y={y0 + boxH / 2 + 12} textAnchor="end"
              fontSize={10} fill="#9ca3af">
              {pctStr(st.count)}
            </text>

            {i < stages.length - 1 && (
              <line x1={mainX + boxW / 2} y1={y0 + boxH}
                x2={mainX + boxW / 2} y2={y0 + boxH + gap}
                stroke="#cbd5e1" strokeWidth={2} markerEnd="url(#a)" />
            )}

            {descLines.map((line, li) => (
              <text key={li} x={descX} y={y0 + boxH / 2 - (descLines.length - 1) * 7 + li * 14}
                textAnchor="start" fontSize={10} fill="#6b7280">
                {line}
              </text>
            ))}

            {st.label === "Briefs" && accumulated && (
              <text x={descX} y={y0 + boxH / 2 + (descLines.length - 0.5) * 14 + 6}
                textAnchor="start" fontSize={9} fill="#9ca3af" fontStyle="italic">
                * incluye briefs de corridas anteriores
              </text>
            )}
          </g>
        );
      })}

      {drops.map((d) => {
        const i = d.fromIdx;
        const y0 = padX + i * (boxH + gap);
        const yC = y0 + boxH / 2;
        return (
          <g key={`drop-${i}`}>
            <line x1={mainX + boxW} y1={yC} x2={dropX} y2={yC}
              stroke="#f87171" strokeWidth={1} strokeDasharray="3,2" markerEnd="url(#ad)" />
            <rect x={dropX} y={yC - dropH / 2} width={dropW} height={dropH} rx={8}
              fill="#fef2f2" stroke="#fca5a5" strokeWidth={1} />
            <text x={dropX + dropW / 2} y={yC - 2} textAnchor="middle"
              fontSize={13} fontWeight={600} fill="#dc2626">
              -{fmt(d.count)}
            </text>
            <text x={dropX + dropW / 2} y={yC + 11} textAnchor="middle"
              fontSize={9} fill="#9ca3af">
              {d.label}
            </text>
          </g>
        );
      })}


    </svg>
  );
};

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
    if (!metrics) return [];
    const isPipelineRun = metrics.data_source === "pipeline_run";
    const lastRun = isPipelineRun && metrics.runs && metrics.runs.length > 0
      ? metrics.runs[metrics.runs.length - 1]
      : null;

    if (lastRun) {
      const briefsStep = lastRun.pipeline.find(s => s.label === "Briefs");
      return [
        { label: "Recolectadas", value: lastRun.pipeline[0]?.value ?? metrics.collected_articles },
        { label: "Utiles", value: lastRun.pipeline[1]?.value ?? metrics.usable_articles },
        { label: "Unicas", value: lastRun.inserted_count ?? lastRun.pipeline[2]?.value ?? metrics.unique_articles },
        { label: "Candidatas", value: lastRun.pipeline[3]?.value ?? metrics.summary_candidates ?? 0 },
        { label: "Briefs", value: lastRun.briefs_count ?? briefsStep?.value ?? metrics.summaries },
      ];
    }

    const rows = getImpactPipelineRows(metrics);
    return rows.filter((row) => ["Recolectadas", "Utiles", "Unicas", "Candidatas", "Briefs"].includes(row.label));
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
                      style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                      <span style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: PIPELINE_COLORS[i % PIPELINE_COLORS.length], flexShrink: 0 }} />
                      <span style={{ fontSize: "0.85rem", color: "#374151" }}>{row.label}</span>
                      <span style={{ fontSize: "0.75rem", color: "#6b7280", marginLeft: "auto" }}>{pctStr}</span>
                      <strong style={{ fontSize: "0.95rem", minWidth: "2.2rem", textAlign: "right" }}>{formatNumber(row.value)}</strong>
                    </div>
                  );
                })}
              </div>
              <div className="pipeline-formulas" style={{ fontSize: "0.8rem", lineHeight: 1.5, color: "#374151", minWidth: "11rem" }}>
                <div style={{ marginBottom: "0.9rem" }}>
                  <strong style={{ fontSize: "0.85rem" }}>Paginas evitadas</strong>
                  <div className="pipeline-formula-row">
                    <div className="pipeline-formula-expression">
                      <div>{formatNumber(metrics.collected_articles)} − {formatNumber(metrics.summaries)} = {formatNumber(metrics.estimated_pages_avoided)}</div>
                      <code style={{ fontSize: "0.75rem", color: "#6b7280" }}>recolectadas − briefs</code>
                    </div>
                    <strong className="pipeline-formula-result" style={{ color: "#006d77" }}>
                      {formatNumber(metrics.estimated_pages_avoided)} paginas evitadas
                    </strong>
                  </div>
                </div>
                <div style={{ marginBottom: "0.9rem" }}>
                  <strong style={{ fontSize: "0.85rem" }}>Reduccion estimada</strong>
                  <div className="pipeline-formula-row">
                    <div className="pipeline-formula-expression">
                      <div>1 − {formatNumber(metrics.summaries)} / {formatNumber(metrics.collected_articles)} = {formatNumber(metrics.reduction_rate * 100)}%</div>
                      <code style={{ fontSize: "0.75rem", color: "#6b7280" }}>1 − briefs / recolectadas</code>
                    </div>
                    <strong className="pipeline-formula-result" style={{ color: "#006d77" }}>
                      {formatNumber(metrics.reduction_rate * 100)}% paginas descartadas
                    </strong>
                  </div>
                </div>
                <div>
                  <strong style={{ fontSize: "0.85rem" }}>Minutos estimados</strong>
                  <div className="pipeline-formula-row">
                    <div className="pipeline-formula-expression">
                      <div>{formatNumber(metrics.estimated_pages_avoided)} × 0.5 <span style={{ color: "#6b7280" }}>(30s c/u)</span> = {formatNumber(metrics.estimated_minutes_saved)}</div>
                      <code style={{ fontSize: "0.75rem", color: "#6b7280" }}>paginas evitadas × 30s</code>
                    </div>
                    <strong className="pipeline-formula-result" style={{ color: "#006d77" }}>
                      {formatNumber(metrics.estimated_minutes_saved)} min de lectura evitada
                    </strong>
                  </div>
                </div>
              </div>
            </div>
            <div className="pipeline-svg-flow">
              <PipelineFlowSVG metrics={metrics} />
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

import { Link } from "../app/router";
import { IconBell, IconCheckCircle, IconClock, IconNews, IconRss, IconShield, IconUsers } from "../components/icons/Icons";
import { SummaryCard } from "../components/news/SummaryCard";
import { SummaryCardSkeleton } from "../components/ui/Skeleton";
import { useGetImpactMetricsQuery, useGetSummariesQuery } from "../services/api";
import { formatNumber } from "../components/indicators/indicatorUtils";

const STEPS = [
  {
    icon: <IconRss size={20} />,
    title: "Recolecta",
    body: "Lee Radio Fides, Unitel, Red Uno, Red Bolivision, Los Tiempos y El Deber, todo el dia.",
  },
  {
    icon: <IconUsers size={20} />,
    title: "Agrupa",
    body: "Detecta cuando dos articulos de fuentes distintas cuentan el mismo hecho y los une en una historia.",
  },
  {
    icon: <IconShield size={20} />,
    title: "Verifica",
    body: "La IA resume y marca cada afirmacion: confirmada por varias fuentes, oficial, o de una sola fuente.",
  },
  {
    icon: <IconBell size={20} />,
    title: "Te llega",
    body: "Por Telegram, WhatsApp, email o la web, en la categoria y la hora que elegiste vos.",
  },
];

export const LandingPage = () => {
  const { data: summariesData, isFetching: isFetchingSummaries } = useGetSummariesQuery({
    fallback_to_latest: true,
    page_size: 4,
  });
  const { data: impact } = useGetImpactMetricsQuery({ fallback_to_latest: true });

  const summaries = summariesData?.items ?? [];

  return (
    <section className="landing-page">
      <section className="landing-hero">
        <span className="landing-kicker">
          <IconNews size={16} />
          Bolivia, sin repetir la misma historia dos veces
        </span>
        <h1>Las noticias de Bolivia, verificadas y sin ruido.</h1>
        <p className="landing-lede">
          EcoBrief lee los principales medios bolivianos, junta las versiones de un mismo hecho en una sola historia,
          y te entrega un resumen con la fuente de cada dato a un clic.
        </p>
        <div className="landing-ctas">
          <Link className="button" href="/panel">
            Ver las noticias de hoy
          </Link>
          <Link className="button secondary" href="/suscribirse">
            Suscribirme gratis
          </Link>
        </div>

        {impact?.has_data && (
          <div className="landing-stat-row">
            <div>
              <strong>{formatNumber(impact.reduction_rate, 0)}%</strong>
              <span>reduccion del flujo</span>
            </div>
            <div>
              <strong>{formatNumber(impact.estimated_pages_avoided, 0)}</strong>
              <span>paginas evitadas hoy</span>
            </div>
            <div>
              <strong>{formatNumber(impact.estimated_minutes_saved, 0)} min</strong>
              <span>de lectura ahorrados</span>
            </div>
          </div>
        )}
      </section>

      <section className="landing-section">
        <div className="section-label">Lo ultimo, resumido y verificado</div>
        <div className="briefs-grid">
          {isFetchingSummaries
            ? Array.from({ length: 4 }, (_, index) => <SummaryCardSkeleton key={index} />)
            : summaries.map((summary) => <SummaryCard key={summary.id ?? summary.title} summary={summary} />)}
        </div>
        {!isFetchingSummaries && summaries.length === 0 && (
          <section className="empty-state compact">
            <span className="panel-title">Sin briefs disponibles todavia</span>
            <p>Volve mas tarde, el sistema procesa noticias durante todo el dia.</p>
          </section>
        )}
      </section>

      <section className="landing-section">
        <div className="section-label">Como funciona</div>
        <div className="landing-steps">
          {STEPS.map((step, index) => (
            <div className="landing-step" key={step.title}>
              <span className="landing-step-number">{index + 1}</span>
              <div className="landing-step-icon">{step.icon}</div>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section landing-trust">
        <div className="section-label">Nos auditamos a nosotros mismos</div>
        <p className="landing-trust-lede">
          La misma disciplina que aplicamos a cada noticia -verificar contra la fuente original- se la aplicamos a
          nuestros propios datos.
        </p>
        <ul className="landing-changelog">
          <li>
            <IconCheckCircle size={16} />
            Corregimos el tipo de cambio oficial: se leia de un reporte bancario desactualizado en vez del valor
            vigente del BCB.
          </li>
          <li>
            <IconCheckCircle size={16} />
            Corregimos el precio de venta en Binance P2P, que tomaba el valor mas bajo en vez del mas alto.
          </li>
          <li>
            <IconClock size={16} />
            Indicadores economicos actualizados cada 10 minutos, con historico verificable en la pagina de Datos.
          </li>
        </ul>
      </section>

      <section className="landing-cta-final">
        <h2>Recibi el resumen del dia, sin abrir diez pestanas.</h2>
        <Link className="button" href="/suscribirse">
          Suscribirme gratis
        </Link>
      </section>
    </section>
  );
};

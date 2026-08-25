import { useState } from "react";

import { trackEvent } from "../../services/analytics";
import type { Story, StoryClaim, StoryConfidenceLevel } from "../../services/types";
import { formatPublishedDate } from "../../utils/date";

const CONFIDENCE_MODIFIER: Record<StoryConfidenceLevel, string> = {
  corrected: "confidence-corrected",
  contradictory: "confidence-contradictory",
  official_statement: "confidence-official",
  multi_source: "confidence-multi",
  single_source: "confidence-single",
  developing: "confidence-developing",
};

type StoryTrustPanelProps = {
  story: Story | undefined;
  isLoading: boolean;
  isError: boolean;
  articleId: number;
};

type ClaimGroupProps = {
  title: string;
  claims: StoryClaim[];
};

const ClaimGroup = ({ title, claims }: ClaimGroupProps) => {
  if (claims.length === 0) {
    return null;
  }

  return (
    <div className="claim-group">
      <span className="claim-group-title">{title}</span>
      <ul className="claim-list">
        {claims.map((claim, index) => (
          <li className="claim-item" key={`${claim.article_id}-${index}`}>
            <p>{claim.claim}</p>
            <a href={claim.source_url} target="_blank" rel="noreferrer">
              Ver fuente
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
};

export const StoryTrustPanel = ({ story, isLoading, isError, articleId }: StoryTrustPanelProps) => {
  const [reportSent, setReportSent] = useState(false);

  const handleReport = () => {
    trackEvent("feedback_submitted", {
      storyId: story?.id ?? String(articleId),
      metadata: { feedback_type: "error_report", article_id: articleId },
    });
    setReportSent(true);
  };

  if (isLoading) {
    return (
      <section className="trust-panel skeleton-panel" aria-hidden="true">
        <span className="skeleton-block skeleton-line skeleton-line-sm" />
        <span className="skeleton-block skeleton-line" />
      </section>
    );
  }

  // Degrada con gracia: si la historia no cargo (404, red, o el articulo no
  // tiene story_cluster_id todavia) simplemente no mostramos el panel, en
  // vez de romper el resto de la pagina de detalle.
  if (isError || !story) {
    return null;
  }

  const hasClaims = story.claims.length > 0;
  const hasCorrections = story.corrections.length > 0;
  const hasMultipleSources = story.sources.length > 1;

  return (
    <section className="trust-panel" aria-label="Trazabilidad y confianza">
      <div className="trust-panel-header">
        <span className="panel-title">Trazabilidad</span>
        <span className={`status-badge ${CONFIDENCE_MODIFIER[story.confidence.level]}`}>
          {story.confidence.label}
        </span>
      </div>

      {story.last_update_note && <p className="trust-update-note">{story.last_update_note}</p>}

      {hasMultipleSources && (
        <div className="trust-sources">
          <span className="trust-section-label">Fuentes que lo confirman ({story.source_count})</span>
          <ul className="trust-sources-list">
            {story.sources.map((source) => (
              <li key={source}>{source}</li>
            ))}
          </ul>
        </div>
      )}

      {hasClaims && (
        <div className="trust-claims">
          <ClaimGroup title="Confirmado por varias fuentes" claims={story.coverage.confirmed_by_multiple_sources} />
          <ClaimGroup title="Basado en comunicado oficial" claims={story.coverage.based_on_official_statement} />
          <ClaimGroup title="Reportado por una sola fuente" claims={story.coverage.reported_by_single_source} />
        </div>
      )}

      {hasCorrections && (
        <div className="trust-corrections">
          <span className="trust-section-label">Historial de correcciones</span>
          <ul className="trust-corrections-list">
            {story.corrections.map((correction, index) => (
              <li key={`${correction.corrected_at}-${index}`}>
                <p>{correction.reason}</p>
                <time dateTime={correction.corrected_at}>{formatPublishedDate(correction.corrected_at)}</time>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="trust-report">
        {reportSent ? (
          <span className="trust-report-confirmation">Gracias, registramos tu observación.</span>
        ) : (
          <button type="button" className="trust-report-button" onClick={handleReport}>
            Reportar un error
          </button>
        )}
      </div>
    </section>
  );
};

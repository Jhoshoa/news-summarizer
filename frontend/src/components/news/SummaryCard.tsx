import { Link } from "../../app/router";
import type { Summary } from "../../services/types";
import { formatPublishedDate } from "../../utils/date";
import { buildContextualSummary, cleanGeneratedText } from "../../utils/summaryText";
import { ArticleImage } from "./ArticleImage";
import { CardMediaFallback, CategoryTag, FactChip, SourceTag } from "./CardParts";

type SummaryCardProps = {
  summary: Summary;
};

export const SummaryCard = ({ summary }: SummaryCardProps) => {
  const href = summary.article_id ? `/article/${summary.article_id}` : summary.url || "#";
  const title = cleanGeneratedText(summary.title);
  const summaryText = buildContextualSummary(summary.summary, summary.article_description);
  const fact = summary.fact ? cleanGeneratedText(summary.fact) : "";
  const hasMultipleSources = (summary.source_count ?? 1) >= 2;
  const content = (
    <>
      <ArticleImage image={summary.image} alt={title} compact />
      <CardMediaFallback category={summary.category} image={summary.image} compact />
      <div>
        <div className="card-meta-row">
          <SourceTag category={summary.category} source={summary.source} />
          <div className="card-badges">
            {hasMultipleSources && (
              <span className="status-badge confidence-multi">Varias fuentes</span>
            )}
            <CategoryTag category={summary.category} />
            <span className="status-badge summarized">Resumido IA</span>
          </div>
        </div>
        <time className="published-date" dateTime={summary.published_at ?? summary.created_at ?? undefined}>
          {formatPublishedDate(summary.published_at ?? summary.created_at)}
        </time>
        <h3>{title}</h3>
        <p>{summaryText}</p>
        <FactChip fact={fact} />
      </div>
    </>
  );

  if (summary.article_id) {
    return (
      <Link className="summary-card card-link" href={href}>
        {content}
      </Link>
    );
  }

  return (
    <a className="summary-card card-link" href={href}>
      {content}
    </a>
  );
};

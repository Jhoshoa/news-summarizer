import { Link } from "../../app/router";
import type { Summary } from "../../services/types";
import { formatPublishedDate } from "../../utils/date";
import { buildContextualSummary, cleanGeneratedText } from "../../utils/summaryText";
import { ArticleImage } from "./ArticleImage";

type SummaryCardProps = {
  summary: Summary;
};

export const SummaryCard = ({ summary }: SummaryCardProps) => {
  const href = summary.article_id ? `/article/${summary.article_id}` : summary.url || "#";
  const title = cleanGeneratedText(summary.title);
  const summaryText = buildContextualSummary(summary.summary, summary.article_description);
  const fact = summary.fact ? cleanGeneratedText(summary.fact) : "";
  const content = (
    <>
      <ArticleImage image={summary.image} alt={title} compact />
      <div>
        <div className="card-meta-row">
          <span className="eyebrow">
            {summary.source ?? "Noticias Bolivia IA"} - {summary.category}
          </span>
          <span className="status-badge summarized">Resumido IA</span>
        </div>
        <time className="published-date" dateTime={summary.published_at ?? summary.created_at ?? undefined}>
          {formatPublishedDate(summary.published_at ?? summary.created_at)}
        </time>
        <h3>{title}</h3>
        <p>{summaryText}</p>
        {fact && <small>{fact}</small>}
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

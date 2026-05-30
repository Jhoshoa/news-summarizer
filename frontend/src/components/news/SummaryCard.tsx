import { Link } from "../../app/router";
import type { Summary } from "../../services/types";
import { formatPublishedDate } from "../../utils/date";
import { ArticleImage } from "./ArticleImage";

type SummaryCardProps = {
  summary: Summary;
};

export const SummaryCard = ({ summary }: SummaryCardProps) => {
  const href = summary.article_id ? `/article/${summary.article_id}` : summary.url || "#";
  const content = (
    <>
      <ArticleImage image={summary.image} alt={summary.title} compact />
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
        <h3>{summary.title}</h3>
        <p>{summary.summary}</p>
        {summary.fact && <small>{summary.fact}</small>}
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

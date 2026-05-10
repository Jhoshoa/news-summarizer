import type { Summary } from "../../services/types";
import { formatPublishedDate } from "../../utils/date";
import { ArticleImage } from "./ArticleImage";

type SummaryCardProps = {
  summary: Summary;
};

export const SummaryCard = ({ summary }: SummaryCardProps) => {
  const href = summary.article_id ? `/article/${summary.article_id}` : summary.url || "#";

  return (
    <article className="summary-card">
      <ArticleImage image={summary.image} alt={summary.title} compact />
      <div>
        <span className="eyebrow">
          {summary.source ?? "Noticias Bolivia IA"} - {summary.category}
        </span>
        <time className="published-date" dateTime={summary.published_at ?? summary.created_at ?? undefined}>
          {formatPublishedDate(summary.published_at ?? summary.created_at)}
        </time>
        <h3>
          <a href={href}>{summary.title}</a>
        </h3>
        <p>{summary.summary}</p>
        {summary.fact && <small>{summary.fact}</small>}
      </div>
    </article>
  );
};

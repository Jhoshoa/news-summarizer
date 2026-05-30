import { Link } from "../../app/router";
import type { Article } from "../../services/types";
import { formatPublishedDate } from "../../utils/date";
import { ArticleImage } from "./ArticleImage";

type NewsCardProps = {
  article: Article;
  isSummarized?: boolean;
};

export const NewsCard = ({ article, isSummarized = false }: NewsCardProps) => (
  <Link className="news-card card-link" href={`/article/${article.id}`}>
    <ArticleImage image={article.image} alt={article.title} compact />
    <div>
      <div className="card-meta-row">
        <span className="eyebrow">
          {article.source} - {article.category}
        </span>
        <span className={`status-badge ${isSummarized ? "summarized" : ""}`}>
          {isSummarized ? "Resumido IA" : "Recolectado"}
        </span>
      </div>
      <time className="published-date" dateTime={article.published_at}>
        {formatPublishedDate(article.published_at)}
      </time>
      <h3>{article.title}</h3>
      <p>{article.description || article.content}</p>
    </div>
  </Link>
);

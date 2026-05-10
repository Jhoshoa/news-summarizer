import type { Article } from "../../services/types";
import { formatPublishedDate } from "../../utils/date";
import { ArticleImage } from "./ArticleImage";

type NewsCardProps = {
  article: Article;
};

export const NewsCard = ({ article }: NewsCardProps) => (
  <article className="news-card">
    <ArticleImage image={article.image} alt={article.title} compact />
    <div>
      <span className="eyebrow">
        {article.source} - {article.category}
      </span>
      <time className="published-date" dateTime={article.published_at}>
        {formatPublishedDate(article.published_at)}
      </time>
      <h3>
        <a href={`/article/${article.id}`}>{article.title}</a>
      </h3>
      <p>{article.description || article.content}</p>
    </div>
  </article>
);

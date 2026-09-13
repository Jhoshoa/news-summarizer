import { getCategoryColor } from "../icons/categoryColors";
import { CategoryIcon } from "../icons/categoryIcons";
import { IconSparkles } from "../icons/Icons";
import { isUsableImageUrl } from "./ArticleImage";

export const CardMediaFallback = ({
  category,
  image,
  compact = false,
}: {
  category?: string | null;
  image?: string | null;
  compact?: boolean;
}) => {
  if (isUsableImageUrl(image)) {
    return null;
  }

  const { bg, fg } = getCategoryColor(category);
  return (
    <div
      className={compact ? "article-image compact card-media-fallback" : "article-image card-media-fallback"}
      style={{ background: bg, color: fg }}
    >
      <CategoryIcon category={category} size={compact ? 26 : 34} />
    </div>
  );
};

export const SourceTag = ({ source, category }: { source?: string | null; category?: string | null }) => (
  <span className="source-tag">
    <CategoryIcon category={category} size={13} />
    {source ?? "EcoBrief Bolivia"}
  </span>
);

export const CategoryTag = ({ category }: { category?: string | null }) => {
  const { bg, fg } = getCategoryColor(category);
  return (
    <span className="category-tag" style={{ background: bg, color: fg }}>
      {category ?? "general"}
    </span>
  );
};

export const FactChip = ({ fact }: { fact?: string | null }) => {
  if (!fact) {
    return null;
  }
  return (
    <div className="fact-chip">
      <IconSparkles size={14} />
      <span>{fact}</span>
    </div>
  );
};

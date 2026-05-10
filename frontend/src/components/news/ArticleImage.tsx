type ArticleImageProps = {
  image?: string | null;
  alt: string;
  compact?: boolean;
};

export const ArticleImage = ({ image, alt, compact = false }: ArticleImageProps) => (
  <div className={compact ? "article-image compact" : "article-image"}>
    {image ? <img src={image} alt={alt} /> : <span aria-hidden="true" />}
  </div>
);

type SkeletonBlockProps = {
  className?: string;
};

const SkeletonBlock = ({ className = "" }: SkeletonBlockProps) => (
  <span className={`skeleton-block ${className}`} aria-hidden="true" />
);

export const NewsCardSkeleton = () => (
  <article className="news-card skeleton-card" aria-hidden="true">
    <SkeletonBlock className="skeleton-media" />
    <div className="skeleton-stack">
      <SkeletonBlock className="skeleton-line skeleton-line-xs" />
      <SkeletonBlock className="skeleton-line skeleton-line-sm" />
      <SkeletonBlock className="skeleton-line skeleton-line-lg" />
      <SkeletonBlock className="skeleton-line" />
      <SkeletonBlock className="skeleton-line skeleton-line-md" />
    </div>
  </article>
);

export const SummaryCardSkeleton = () => (
  <article className="summary-card skeleton-card" aria-hidden="true">
    <SkeletonBlock className="skeleton-media" />
    <div className="skeleton-stack">
      <SkeletonBlock className="skeleton-line skeleton-line-xs" />
      <SkeletonBlock className="skeleton-line skeleton-line-sm" />
      <SkeletonBlock className="skeleton-line skeleton-line-lg" />
      <SkeletonBlock className="skeleton-line" />
      <SkeletonBlock className="skeleton-line skeleton-line-md" />
    </div>
  </article>
);

export const MarketSkeletons = () => (
  <section className="markets" aria-label="Cargando tipos de cambio">
    {Array.from({ length: 3 }, (_, index) => (
      <article className="market skeleton-panel" key={index} aria-hidden="true">
        <SkeletonBlock className="skeleton-line skeleton-line-sm" />
        <div className="rate-pair">
          <div>
            <SkeletonBlock className="skeleton-line skeleton-line-xs" />
            <SkeletonBlock className="skeleton-line skeleton-line-md" />
          </div>
          <div>
            <SkeletonBlock className="skeleton-line skeleton-line-xs" />
            <SkeletonBlock className="skeleton-line skeleton-line-md" />
          </div>
        </div>
        <SkeletonBlock className="skeleton-line skeleton-line-sm" />
      </article>
    ))}
  </section>
);

export const MiniIndicatorSkeletons = () => (
  <section className="mini-grid" aria-label="Cargando indicadores">
    {Array.from({ length: 4 }, (_, index) => (
      <article className="mini-indicator skeleton-panel" key={index} aria-hidden="true">
        <SkeletonBlock className="skeleton-line skeleton-line-sm" />
        <SkeletonBlock className="skeleton-line skeleton-line-md" />
        <SkeletonBlock className="skeleton-line skeleton-line-xs" />
      </article>
    ))}
  </section>
);

export const PanelSkeleton = () => (
  <section className="data-panel skeleton-panel" aria-hidden="true">
    <SkeletonBlock className="skeleton-line skeleton-line-sm" />
    <SkeletonBlock className="skeleton-line skeleton-line-xl" />
    <div className="metric-list">
      {Array.from({ length: 3 }, (_, index) => (
        <div key={index}>
          <SkeletonBlock className="skeleton-line skeleton-line-sm" />
          <SkeletonBlock className="skeleton-line skeleton-line-md" />
        </div>
      ))}
    </div>
  </section>
);

export const TableSkeleton = () => (
  <section className="data-panel wide-panel skeleton-panel" aria-hidden="true">
    <SkeletonBlock className="skeleton-line skeleton-line-md" />
    <div className="skeleton-table">
      {Array.from({ length: 6 }, (_, index) => (
        <SkeletonBlock className="skeleton-line" key={index} />
      ))}
    </div>
  </section>
);

export const ArticleDetailSkeleton = () => (
  <section className="detail-layout" aria-label="Cargando articulo">
    <article className="detail-article skeleton-detail" aria-hidden="true">
      <SkeletonBlock className="skeleton-line skeleton-line-xs" />
      <SkeletonBlock className="skeleton-line skeleton-line-sm" />
      <SkeletonBlock className="skeleton-line skeleton-title" />
      <SkeletonBlock className="skeleton-line skeleton-title skeleton-title-short" />
      <section className="article-content-layout has-image">
        <div className="article-text-column">
          <section className="ai-summary skeleton-panel">
            <SkeletonBlock className="skeleton-line skeleton-line-sm" />
            <SkeletonBlock className="skeleton-line" />
            <SkeletonBlock className="skeleton-line" />
            <SkeletonBlock className="skeleton-line skeleton-line-md" />
          </section>
          <section className="article-body">
            {Array.from({ length: 5 }, (_, index) => (
              <SkeletonBlock className="skeleton-line" key={index} />
            ))}
          </section>
        </div>
        <aside className="article-media-column">
          <SkeletonBlock className="skeleton-image-large" />
        </aside>
      </section>
    </article>
    <aside className="detail-sidebar">
      <PanelSkeleton />
      <PanelSkeleton />
      <PanelSkeleton />
    </aside>
  </section>
);

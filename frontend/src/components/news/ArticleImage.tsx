import { useState } from "react";

type ArticleImageProps = {
  image?: string | null;
  alt: string;
  compact?: boolean;
};

const blockedImageHosts = ["tracker.metricool.com"];
const blockedImagePatterns = ["/c3po.jpg", "pixel", "tracker", "analytics"];

const isUsableImageUrl = (value?: string | null) => {
  const imageUrl = value?.trim();
  if (!imageUrl) {
    return false;
  }

  try {
    const url = new URL(imageUrl);
    const normalized = imageUrl.toLowerCase();
    return (
      !blockedImageHosts.includes(url.hostname.toLowerCase()) &&
      !blockedImagePatterns.some((pattern) => normalized.includes(pattern))
    );
  } catch {
    return false;
  }
};

export const ArticleImage = ({ image, alt, compact = false }: ArticleImageProps) => {
  const [failed, setFailed] = useState(false);
  const imageUrl = image?.trim();

  if (!isUsableImageUrl(imageUrl) || failed) {
    return null;
  }

  return (
    <div className={compact ? "article-image compact" : "article-image"}>
      <img src={imageUrl} alt={alt} onError={() => setFailed(true)} />
    </div>
  );
};

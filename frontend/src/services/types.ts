export type EconomicIndicator = {
  id: number;
  source: string;
  indicator_code: string;
  indicator_name: string;
  indicator_group: string;
  value: number;
  unit: string | null;
  currency: string | null;
  asset: string | null;
  side: string | null;
  observed_at: string | null;
  collected_at: string;
  snapshot_key: string;
  raw_payload: Record<string, unknown>;
};

export type EconomicIndicatorsResponse = {
  count: number;
  date?: string | null;
  items: EconomicIndicator[];
};

export type WeatherLocation = {
  key: string;
  name: string;
  department: string;
  country: string;
  latitude: number;
  longitude: number;
};

export type WeatherResponse = {
  location: WeatherLocation;
  current: Record<string, number | string>;
  today: {
    temperature_max: number | null;
    temperature_min: number | null;
    uv_index_max: number | null;
    precipitation_sum: number | null;
  };
  radiation: {
    uv_index: number | null;
    uv_index_clear_sky: number | null;
    shortwave_radiation: number | null;
    direct_radiation: number | null;
  };
  units: {
    current: Record<string, string>;
    hourly: Record<string, string>;
    daily: Record<string, string>;
  };
  raw_payload: Record<string, unknown>;
};

export type WeatherLocationsResponse = {
  items: WeatherLocation[];
};

export type ImpactPipelineStep = {
  label: string;
  value: number;
};

export type ImpactMethodology = {
  minutes_per_article: number;
  mb_per_page: number;
  note: string;
};

export type ImpactMetricsRun = {
  started_at: string | null;
  finished_at: string | null;
  time: string;
  cache_reused: boolean;
  briefs_count?: number;
  inserted_count?: number;
  updated_count?: number;
  duplicate_dropped_count?: number;
  ranked_count?: number;
  pipeline: ImpactPipelineStep[];
};

export type ImpactMetricsResponse = {
  date: string;
  requested_date: string;
  is_fallback: boolean;
  has_data: boolean;
  data_source?: "pipeline_run" | "derived" | "empty";
  collected_articles: number;
  unique_articles: number;
  summaries: number;
  quality_dropped_articles?: number;
  duplicate_articles?: number;
  summary_candidates?: number;
  usable_articles?: number;
  ranked_articles?: number;
  inserted_articles?: number;
  updated_articles?: number;
  duplicate_articles_estimated: number;
  reduction_rate: number;
  estimated_pages_avoided: number;
  estimated_minutes_saved: number;
  estimated_data_saved_mb: number;
  cache_reused: boolean;
  ai_calls_avoided_estimated: number;
  llm_provider?: string | null;
  llm_model?: string | null;
  pipeline: ImpactPipelineStep[];
  methodology: ImpactMethodology;
  runs?: ImpactMetricsRun[];
};

export type PreferenceOption = {
  slug: string;
  label: string;
  enabled: boolean;
  note?: string | null;
};

export type PreferenceOptionsResponse = {
  categories: PreferenceOption[];
  channels: PreferenceOption[];
  frequencies: PreferenceOption[];
  preferred_hours: PreferenceOption[];
};

export type SubscribeRequest = {
  channel: "whatsapp" | "telegram" | "email";
  phone?: string | null;
  telegram_id?: string | null;
  email?: string | null;
  categories: string[];
  frequency: string;
  preferred_hour: number;
  timezone: string;
  consent_accepted: boolean;
};

export type SubscribeResponse = {
  status: "saved";
  channel: "whatsapp" | "telegram";
  categories: string[];
  frequency: string;
  preferred_hour: number;
  message: string;
};

export type UnsubscribeRequest = {
  channel: "whatsapp" | "telegram" | "email";
  identifier: string;
};

export type UnsubscribeResponse = {
  status: "unsubscribed";
  message: string;
};

export type PreferencePreviewRequest = {
  categories: string[];
};

export type PreferencePreviewItem = {
  category: string;
  title: string;
  summary: string;
  fact?: string | null;
  summary_date?: string | null;
};

export type PreferencePreviewResponse = {
  items: PreferencePreviewItem[];
  has_data: boolean;
  message: string;
};

export type CategoryCount = {
  slug: string;
  label: string;
  count: number;
};

export type CategoryCountsResponse = {
  counts: CategoryCount[];
  total: number;
  date: string;
  requested_date: string;
  is_fallback: boolean;
};

export type PaginatedResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  date?: string | null;
  requested_date?: string | null;
  is_fallback?: boolean;
};

export type Article = {
  id: number;
  title: string;
  url: string;
  description?: string | null;
  content?: string | null;
  image?: string | null;
  published_at: string;
  collected_at?: string;
  source: string;
  category: string;
  score?: number;
  source_count?: number;
};

export type RelatedArticleItem = {
  id: number;
  title: string;
  url: string;
  source: string;
  published_at: string;
  duplicate_of_article_id?: number | null;
};

export type RelatedArticles = {
  story_cluster_id: string | null;
  canonical_article_id: number;
  items: RelatedArticleItem[];
};

export type Summary = {
  id?: number;
  article_id?: number | null;
  category: string;
  title: string;
  summary: string;
  fact?: string | null;
  source?: string | null;
  url?: string | null;
  article_title?: string | null;
  article_description?: string | null;
  published_at?: string | null;
  image?: string | null;
  summary_date?: string | null;
  created_at?: string | null;
  story_cluster_id?: string | null;
  source_count?: number;
};

export type StoryConfidenceLevel =
  | "corrected"
  | "contradictory"
  | "official_statement"
  | "multi_source"
  | "single_source"
  | "developing";

export type StoryConfidence = {
  level: StoryConfidenceLevel;
  label: string;
};

export type StoryClaim = {
  claim: string;
  confidence: StoryConfidenceLevel;
  claim_type?: string | null;
  article_id: number;
  source_url: string;
  source_excerpt?: string | null;
  published_at?: string | null;
};

export type StoryArticleRef = {
  article_id: number;
  title: string;
  url: string;
  source: string;
  author?: string | null;
  published_at?: string | null;
  relationship_type: string;
  similarity_score?: number | null;
  is_update: boolean;
};

export type StoryCoverage = {
  source_count: number;
  sources: string[];
  confirmed_by_multiple_sources: StoryClaim[];
  based_on_official_statement: StoryClaim[];
  reported_by_single_source: StoryClaim[];
};

export type StoryCorrection = {
  reason: string;
  corrected_by?: string | null;
  corrected_at: string;
};

export type Story = {
  id: string;
  canonical_title: string;
  short_summary?: string | null;
  detailed_summary?: string | null;
  category?: string | null;
  country: string;
  current_status: string;
  confidence: StoryConfidence;
  first_published_at: string;
  last_updated_at: string;
  last_update_note?: string | null;
  article_count: number;
  source_count: number;
  sources: string[];
  articles: StoryArticleRef[];
  claims: StoryClaim[];
  coverage: StoryCoverage;
  corrections: StoryCorrection[];
};

export type Source = {
  name: string;
  url: string;
  category: string;
  country: string;
  enabled: boolean;
};

export type SourcesResponse = {
  items: Source[];
};

export type TriggerSummaryResponse = {
  status: string;
  message: string;
  job?: {
    id: string;
    status: string;
    time_of_day: string;
    refresh: boolean;
    requested_at?: string | null;
    started_at?: string | null;
    finished_at?: string | null;
    result?: Record<string, unknown> | null;
    error_message?: string | null;
  };
  status_url?: string;
  result?: {
    collected: number;
    processed?: number;
    summaries: number;
    sent: number;
    collection_stats?: {
      scraper: number;
      newsapi: number;
      inserted: number;
      updated: number;
    };
  };
};

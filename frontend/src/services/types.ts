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
};

export type TriggerSummaryResponse = {
  status: string;
  message: string;
  result: {
    collected: number;
    processed: number;
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

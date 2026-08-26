import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import type {
  Article,
  CategoryCountsResponse,
  EconomicIndicatorsResponse,
  ImpactMetricsResponse,
  PaginatedResponse,
  PreferenceOptionsResponse,
  PreferencePreviewRequest,
  PreferencePreviewResponse,
  SourcesResponse,
  Story,
  Summary,
  SubscribeRequest,
  SubscribeResponse,
  TriggerSummaryResponse,
  UnsubscribeRequest,
  UnsubscribeResponse,
  WeatherLocationsResponse,
  WeatherResponse,
} from "./types";

type GetIndicatorsArgs = {
  date?: string | null;
};

type GetArticlesArgs = {
  category?: string;
  date?: string;
  source?: string;
  q?: string;
  fallback_to_latest?: boolean;
  exclude_summarized?: boolean;
  page?: number;
  page_size?: number;
  limit?: number;
};

type GetSummariesArgs = {
  category?: string;
  date?: string;
  article_id?: number;
  fallback_to_latest?: boolean;
  page?: number;
  page_size?: number;
};

type GetCategoryCountsArgs = {
  view?: "resumenes" | "recolectadas";
  date?: string;
  fallback_to_latest?: boolean;
};

type GetImpactMetricsArgs = {
  date?: string;
  fallback_to_latest?: boolean;
};

type TriggerSummaryArgs = {
  async_mode?: boolean;
  refresh?: boolean;
  time_of_day?: string;
};

export const newsApi = createApi({
  reducerPath: "newsApi",
  baseQuery: fetchBaseQuery({
    baseUrl: import.meta.env.VITE_API_BASE_URL || "",
  }),
  tagTypes: ["EconomicIndicators", "Weather", "Articles", "Summaries", "ImpactMetrics", "Preferences", "Sources", "Stories"],
  endpoints: (builder) => ({
    getEconomicIndicators: builder.query<EconomicIndicatorsResponse, GetIndicatorsArgs | void>({
      query: (args) => ({
        url: "/api/economic-indicators",
        params: args?.date ? { date: args.date } : undefined,
      }),
      providesTags: ["EconomicIndicators"],
    }),
    refreshEconomicIndicators: builder.mutation<EconomicIndicatorsResponse, void>({
      query: () => ({
        url: "/api/economic-indicators/refresh",
        method: "POST",
      }),
      invalidatesTags: ["EconomicIndicators"],
    }),
    getWeather: builder.query<WeatherResponse, string | void>({
      query: (location) => ({
        url: "/api/weather",
        params: location ? { location } : undefined,
      }),
      providesTags: ["Weather"],
    }),
    getWeatherLocations: builder.query<WeatherLocationsResponse, void>({
      query: () => "/api/weather/locations",
      providesTags: ["Weather"],
    }),
    getArticles: builder.query<PaginatedResponse<Article>, GetArticlesArgs | void>({
      query: (args) => ({
        url: "/api/articles",
        params: {
          category: args?.category,
          date: args?.date,
          source: args?.source,
          q: args?.q,
          fallback_to_latest: args?.fallback_to_latest,
          exclude_summarized: args?.exclude_summarized,
          page: args?.page ?? 1,
          page_size: args?.page_size ?? args?.limit ?? 20,
        },
      }),
      providesTags: ["Articles"],
    }),
    getArticleById: builder.query<Article, number>({
      query: (id) => `/api/articles/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Articles", id }],
    }),
    getStoryById: builder.query<Story, string>({
      query: (storyId) => `/api/stories/${storyId}`,
      providesTags: (_result, _error, storyId) => [{ type: "Stories", id: storyId }],
    }),
    getSummaries: builder.query<PaginatedResponse<Summary>, GetSummariesArgs | void>({
      query: (args) => ({
        url: "/api/summaries",
        params: {
          category: args?.category,
          date: args?.date,
          article_id: args?.article_id,
          fallback_to_latest: args?.fallback_to_latest,
          page: args?.page ?? 1,
          page_size: args?.page_size ?? 20,
        },
      }),
      providesTags: ["Summaries"],
    }),
    getSources: builder.query<SourcesResponse, void>({
      query: () => "/api/sources",
      providesTags: ["Sources"],
    }),
    getCategoryCounts: builder.query<CategoryCountsResponse, GetCategoryCountsArgs | void>({
      query: (args) => ({
        url: "/api/news/category-counts",
        params: {
          view: args?.view ?? "resumenes",
          date: args?.date,
          fallback_to_latest: args?.fallback_to_latest,
        },
      }),
      providesTags: ["Articles", "Summaries"],
    }),
    getImpactMetrics: builder.query<ImpactMetricsResponse, GetImpactMetricsArgs | void>({
      query: (args) => ({
        url: "/api/impact-metrics",
        params: {
          date: args?.date,
          fallback_to_latest: args?.fallback_to_latest ?? true,
        },
      }),
      keepUnusedDataFor: 0,
      providesTags: ["ImpactMetrics"],
    }),
    getPreferenceOptions: builder.query<PreferenceOptionsResponse, void>({
      query: () => "/api/preferences/options",
      providesTags: ["Preferences"],
    }),
    subscribeToBrief: builder.mutation<SubscribeResponse, SubscribeRequest>({
      query: (body) => ({
        url: "/api/preferences/subscribe",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Preferences"],
    }),
    unsubscribeFromBrief: builder.mutation<UnsubscribeResponse, UnsubscribeRequest>({
      query: (body) => ({
        url: "/api/preferences/unsubscribe",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Preferences"],
    }),
    previewPreferences: builder.mutation<PreferencePreviewResponse, PreferencePreviewRequest>({
      query: (body) => ({
        url: "/api/preferences/preview",
        method: "POST",
        body,
      }),
    }),
    triggerSummary: builder.mutation<TriggerSummaryResponse, TriggerSummaryArgs | void>({
      query: (args) => ({
        url: "/trigger/summary",
        method: "POST",
        params: {
          time_of_day: args?.time_of_day ?? "manual",
          refresh: args?.refresh ?? true,
          async_mode: args?.async_mode,
        },
      }),
      invalidatesTags: ["Articles", "Summaries", "ImpactMetrics"],
    }),
  }),
});

export const {
  useGetEconomicIndicatorsQuery,
  useRefreshEconomicIndicatorsMutation,
  useGetWeatherQuery,
  useGetWeatherLocationsQuery,
  useGetArticlesQuery,
  useGetArticleByIdQuery,
  useGetStoryByIdQuery,
  useGetSummariesQuery,
  useGetImpactMetricsQuery,
  useGetPreferenceOptionsQuery,
  useGetSourcesQuery,
  useGetCategoryCountsQuery,
  usePreviewPreferencesMutation,
  useTriggerSummaryMutation,
  useSubscribeToBriefMutation,
  useUnsubscribeFromBriefMutation,
} = newsApi;

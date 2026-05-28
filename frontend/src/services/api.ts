import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import type {
  Article,
  EconomicIndicatorsResponse,
  PaginatedResponse,
  Summary,
  TriggerSummaryResponse,
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
  page?: number;
  page_size?: number;
  limit?: number;
};

type GetSummariesArgs = {
  category?: string;
  date?: string;
  article_id?: number;
  page?: number;
  page_size?: number;
};

type TriggerSummaryArgs = {
  refresh?: boolean;
  time_of_day?: string;
};

export const newsApi = createApi({
  reducerPath: "newsApi",
  baseQuery: fetchBaseQuery({
    baseUrl: import.meta.env.VITE_API_BASE_URL || "",
  }),
  tagTypes: ["EconomicIndicators", "Weather", "Articles", "Summaries"],
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
    getSummaries: builder.query<PaginatedResponse<Summary>, GetSummariesArgs | void>({
      query: (args) => ({
        url: "/api/summaries",
        params: {
          category: args?.category,
          date: args?.date,
          article_id: args?.article_id,
          page: args?.page ?? 1,
          page_size: args?.page_size ?? 20,
        },
      }),
      providesTags: ["Summaries"],
    }),
    triggerSummary: builder.mutation<TriggerSummaryResponse, TriggerSummaryArgs | void>({
      query: (args) => ({
        url: "/trigger/summary",
        method: "POST",
        params: {
          time_of_day: args?.time_of_day ?? "manual",
          refresh: args?.refresh ?? true,
        },
      }),
      invalidatesTags: ["Articles", "Summaries"],
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
  useGetSummariesQuery,
  useTriggerSummaryMutation,
} = newsApi;

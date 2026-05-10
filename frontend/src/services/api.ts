import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import type {
  Article,
  EconomicIndicatorsResponse,
  PaginatedResponse,
  Summary,
  WeatherLocationsResponse,
  WeatherResponse,
} from "./types";

type GetIndicatorsArgs = {
  date?: string | null;
};

type GetArticlesArgs = {
  category?: string;
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
} = newsApi;

import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import type {
  Article,
  EconomicIndicatorsResponse,
  Summary,
  WeatherLocationsResponse,
  WeatherResponse,
} from "./types";

type GetIndicatorsArgs = {
  date?: string | null;
};

type GetArticlesArgs = {
  category?: string;
  limit?: number;
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
    getArticles: builder.query<Article[], GetArticlesArgs | void>({
      query: (args) => ({
        url: "/api/articles",
        params: {
          category: args?.category,
          limit: args?.limit ?? 20,
        },
      }),
      providesTags: ["Articles"],
    }),
    getArticleById: builder.query<Article, number>({
      query: (id) => `/api/articles/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Articles", id }],
    }),
    getSummaries: builder.query<Summary[], { category?: string } | void>({
      query: (args) => ({
        url: "/api/summaries",
        params: args?.category ? { category: args.category } : undefined,
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

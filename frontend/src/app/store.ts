import { configureStore } from "@reduxjs/toolkit";

import { newsApi } from "../services/api";
import uiReducer from "../features/ui/uiSlice";

export const store = configureStore({
  reducer: {
    ui: uiReducer,
    [newsApi.reducerPath]: newsApi.reducer,
  },
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(newsApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

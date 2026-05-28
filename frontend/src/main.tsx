import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";

import App from "./App";
import { RefreshControlProvider } from "./app/refreshControl";
import { RouterProvider } from "./app/router";
import { store } from "./app/store";
import "./styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <RouterProvider>
        <RefreshControlProvider>
          <App />
        </RefreshControlProvider>
      </RouterProvider>
    </Provider>
  </StrictMode>,
);

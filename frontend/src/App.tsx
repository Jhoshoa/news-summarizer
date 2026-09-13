import { useEffect } from "react";

import { useRefreshControlContext } from "./app/refreshControl";
import { useRouter } from "./app/router";
import { AppShell } from "./components/layout/AppShell";
import { ArticleDetailPage } from "./pages/ArticleDetailPage";
import { DataPage } from "./pages/DataPage";
import { HomePage } from "./pages/HomePage";
import { ImpactPage } from "./pages/ImpactPage";
import { NewsPage } from "./pages/NewsPage";
import { FuentesPage } from "./pages/FuentesPage";
import { SubscribePage } from "./pages/SubscribePage";
import { getNavigationState } from "./utils/navigation";

const manualRefreshEnabled = import.meta.env.VITE_ENABLE_MANUAL_REFRESH === "true";

const App = () => {
  const { location, replace } = useRouter();
  const { isRefreshing, onRefresh } = useRefreshControlContext();
  const isArticleRoute = location.pathname.startsWith("/article");
  const isNewsRoute = location.pathname.startsWith("/news");
  const isDataRoute = location.pathname.startsWith("/datos");
  const isImpactRoute = location.pathname.startsWith("/impacto");
  const isFuentesRoute = location.pathname.startsWith("/fuentes");
  const isSubscribeRoute = location.pathname.startsWith("/suscribirse");
  // /panel se fusiono con la landing en "/" (una sola pagina de inicio, no dos
  // que se repetian). Se mantiene el redirect para no romper enlaces viejos.
  const isLegacyPanelRoute = location.pathname.startsWith("/panel");
  const isHomeRoute =
    !isArticleRoute &&
    !isNewsRoute &&
    !isDataRoute &&
    !isImpactRoute &&
    !isFuentesRoute &&
    !isSubscribeRoute &&
    !isLegacyPanelRoute;
  const compactHeader =
    isArticleRoute || isNewsRoute || isDataRoute || isImpactRoute || isFuentesRoute || isSubscribeRoute;
  const navigationState = getNavigationState(location.pathname);

  useEffect(() => {
    if (isLegacyPanelRoute) {
      replace("/");
    }
  }, [isLegacyPanelRoute, replace]);

  let page = <HomePage />;

  if (isArticleRoute) {
    page = <ArticleDetailPage />;
  } else if (isNewsRoute) {
    page = <NewsPage />;
  } else if (isDataRoute) {
    page = <DataPage />;
  } else if (isImpactRoute) {
    page = <ImpactPage />;
  } else if (isFuentesRoute) {
    page = <FuentesPage />;
  } else if (isSubscribeRoute) {
    page = <SubscribePage />;
  } else if (isHomeRoute || isLegacyPanelRoute) {
    page = <HomePage />;
  }

  return (
    <AppShell
      activePath={navigationState.activePath}
      backFallback={navigationState.backFallback}
      breadcrumbs={navigationState.breadcrumbs}
      compactHeader={compactHeader}
      isRefreshing={manualRefreshEnabled ? isRefreshing : false}
      onRefresh={manualRefreshEnabled ? onRefresh : undefined}
      showTrail={!isHomeRoute}
    >
      {page}
    </AppShell>
  );
};

export default App;

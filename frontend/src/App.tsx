import { useRefreshControlContext } from "./app/refreshControl";
import { useRouter } from "./app/router";
import { AppShell } from "./components/layout/AppShell";
import { ArticleDetailPage } from "./pages/ArticleDetailPage";
import { DataPage } from "./pages/DataPage";
import { HomePage } from "./pages/HomePage";
import { ImpactPage } from "./pages/ImpactPage";
import { NewsPage } from "./pages/NewsPage";
import { getNavigationState } from "./utils/navigation";

const App = () => {
  const { location } = useRouter();
  const { isRefreshing, onRefresh } = useRefreshControlContext();
  const isArticleRoute = location.pathname.startsWith("/article");
  const isNewsRoute = location.pathname.startsWith("/news");
  const isDataRoute = location.pathname.startsWith("/datos");
  const isImpactRoute = location.pathname.startsWith("/impacto");
  const compactHeader = isArticleRoute || isNewsRoute || isDataRoute || isImpactRoute;
  const navigationState = getNavigationState(location.pathname);

  let page = <HomePage />;

  if (isArticleRoute) {
    page = <ArticleDetailPage />;
  } else if (isNewsRoute) {
    page = <NewsPage />;
  } else if (isDataRoute) {
    page = <DataPage />;
  } else if (isImpactRoute) {
    page = <ImpactPage />;
  }

  return (
    <AppShell
      activePath={navigationState.activePath}
      backFallback={navigationState.backFallback}
      breadcrumbs={navigationState.breadcrumbs}
      compactHeader={compactHeader}
      isRefreshing={isRefreshing}
      onRefresh={onRefresh}
    >
      {page}
    </AppShell>
  );
};

export default App;

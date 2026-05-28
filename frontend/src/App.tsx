import { useRefreshControlContext } from "./app/refreshControl";
import { useRouter } from "./app/router";
import { AppShell } from "./components/layout/AppShell";
import { ArticleDetailPage } from "./pages/ArticleDetailPage";
import { DataPage } from "./pages/DataPage";
import { HomePage } from "./pages/HomePage";
import { NewsPage } from "./pages/NewsPage";

const App = () => {
  const { location } = useRouter();
  const { isRefreshing, onRefresh } = useRefreshControlContext();
  const isArticleRoute = location.pathname.startsWith("/article");
  const isNewsRoute = location.pathname.startsWith("/news");
  const isDataRoute = location.pathname.startsWith("/datos");
  const compactHeader = isArticleRoute || isNewsRoute || isDataRoute;

  let page = <HomePage />;

  if (isArticleRoute) {
    page = <ArticleDetailPage />;
  } else if (isNewsRoute) {
    page = <NewsPage />;
  } else if (isDataRoute) {
    page = <DataPage />;
  }

  return (
    <AppShell compactHeader={compactHeader} isRefreshing={isRefreshing} onRefresh={onRefresh}>
      {page}
    </AppShell>
  );
};

export default App;

import { ArticleDetailPage } from "./pages/ArticleDetailPage";
import { DataPage } from "./pages/DataPage";
import { HomePage } from "./pages/HomePage";
import { NewsPage } from "./pages/NewsPage";

const App = () => {
  const isArticleRoute = window.location.pathname.startsWith("/article");
  const isNewsRoute = window.location.pathname.startsWith("/news");
  const isDataRoute = window.location.pathname.startsWith("/datos");

  if (isArticleRoute) {
    return <ArticleDetailPage />;
  }

  if (isNewsRoute) {
    return <NewsPage />;
  }

  if (isDataRoute) {
    return <DataPage />;
  }

  return <HomePage />;
};

export default App;

import { ArticleDetailPage } from "./pages/ArticleDetailPage";
import { HomePage } from "./pages/HomePage";
import { NewsPage } from "./pages/NewsPage";

const App = () => {
  const isArticleRoute = window.location.pathname.startsWith("/article");
  const isNewsRoute = window.location.pathname.startsWith("/news");

  if (isArticleRoute) {
    return <ArticleDetailPage />;
  }

  if (isNewsRoute) {
    return <NewsPage />;
  }

  return <HomePage />;
};

export default App;

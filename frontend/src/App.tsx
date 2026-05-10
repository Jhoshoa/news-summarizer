import { ArticleDetailPage } from "./pages/ArticleDetailPage";
import { HomePage } from "./pages/HomePage";

const App = () => {
  const isArticleRoute = window.location.pathname.startsWith("/article");

  return isArticleRoute ? <ArticleDetailPage /> : <HomePage />;
};

export default App;

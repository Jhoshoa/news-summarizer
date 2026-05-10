import type { ReactNode } from "react";

import { Footer } from "./Footer";
import { Header } from "./Header";

type AppShellProps = {
  children: ReactNode;
  compactHeader?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void;
};

export const AppShell = ({
  children,
  compactHeader = false,
  isRefreshing = false,
  onRefresh,
}: AppShellProps) => (
  <div className="app-frame">
    <Header compact={compactHeader} isRefreshing={isRefreshing} onRefresh={onRefresh} />
    <main className="page">{children}</main>
    <Footer />
  </div>
);

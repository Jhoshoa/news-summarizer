import type { ReactNode } from "react";

import type { BreadcrumbItem, NavigationState } from "../../utils/navigation";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { NavigationTrail } from "./NavigationTrail";

type AppShellProps = {
  activePath?: NavigationState["activePath"];
  backFallback?: string;
  breadcrumbs?: BreadcrumbItem[];
  children: ReactNode;
  compactHeader?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void;
};

export const AppShell = ({
  activePath = "/",
  backFallback = "/",
  breadcrumbs = [{ href: "/", label: "Inicio" }],
  children,
  compactHeader = false,
  isRefreshing = false,
  onRefresh,
}: AppShellProps) => (
  <div className="app-frame">
    <Header
      activePath={activePath}
      compact={compactHeader}
      isRefreshing={isRefreshing}
      onRefresh={onRefresh}
    />
    <NavigationTrail backFallback={backFallback} breadcrumbs={breadcrumbs} />
    <main className="page">{children}</main>
    <Footer />
  </div>
);

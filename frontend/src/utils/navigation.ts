export type BreadcrumbItem = {
  href: string;
  label: string;
};

export type NavigationState = {
  activePath: "/" | "/news" | "/datos" | "/impacto" | "/suscribirse" | "/article";
  backFallback: string;
  breadcrumbs: BreadcrumbItem[];
};

export const getNavigationState = (pathname: string): NavigationState => {
  if (pathname.startsWith("/article")) {
    return {
      activePath: "/article",
      backFallback: "/news",
      breadcrumbs: [
        { href: "/", label: "Inicio" },
        { href: "/news", label: "Noticias" },
        { href: pathname, label: "Detalle" },
      ],
    };
  }

  if (pathname.startsWith("/news")) {
    return {
      activePath: "/news",
      backFallback: "/",
      breadcrumbs: [
        { href: "/", label: "Inicio" },
        { href: "/news", label: "Noticias" },
      ],
    };
  }

  if (pathname.startsWith("/datos")) {
    return {
      activePath: "/datos",
      backFallback: "/",
      breadcrumbs: [
        { href: "/", label: "Inicio" },
        { href: "/datos", label: "Datos" },
      ],
    };
  }

  if (pathname.startsWith("/impacto")) {
    return {
      activePath: "/impacto",
      backFallback: "/",
      breadcrumbs: [
        { href: "/", label: "Inicio" },
        { href: "/impacto", label: "Impacto" },
      ],
    };
  }

  if (pathname.startsWith("/suscribirse")) {
    return {
      activePath: "/suscribirse",
      backFallback: "/",
      breadcrumbs: [
        { href: "/", label: "Inicio" },
        { href: "/suscribirse", label: "Suscribirse" },
      ],
    };
  }

  return {
    activePath: "/",
    backFallback: "/",
    breadcrumbs: [{ href: "/", label: "Inicio" }],
  };
};

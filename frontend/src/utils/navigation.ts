export type BreadcrumbItem = {
  href: string;
  label: string;
};

export type NavigationState = {
  activePath: "/" | "/panel" | "/news" | "/datos" | "/impacto" | "/fuentes" | "/suscribirse" | "/article";
  backFallback: string;
  breadcrumbs: BreadcrumbItem[];
};

export const getNavigationState = (pathname: string): NavigationState => {
  if (pathname.startsWith("/article")) {
    return {
      activePath: "/article",
      backFallback: "/news",
      breadcrumbs: [
        { href: "/panel", label: "Inicio" },
        { href: "/news", label: "Noticias" },
        { href: pathname, label: "Detalle" },
      ],
    };
  }

  if (pathname.startsWith("/news")) {
    return {
      activePath: "/news",
      backFallback: "/panel",
      breadcrumbs: [
        { href: "/panel", label: "Inicio" },
        { href: "/news", label: "Noticias" },
      ],
    };
  }

  if (pathname.startsWith("/datos")) {
    return {
      activePath: "/datos",
      backFallback: "/panel",
      breadcrumbs: [
        { href: "/panel", label: "Inicio" },
        { href: "/datos", label: "Datos" },
      ],
    };
  }

  if (pathname.startsWith("/impacto")) {
    return {
      activePath: "/impacto",
      backFallback: "/panel",
      breadcrumbs: [
        { href: "/panel", label: "Inicio" },
        { href: "/impacto", label: "Impacto" },
      ],
    };
  }

  if (pathname.startsWith("/fuentes")) {
    return {
      activePath: "/fuentes",
      backFallback: "/panel",
      breadcrumbs: [
        { href: "/panel", label: "Inicio" },
        { href: "/fuentes", label: "Fuentes" },
      ],
    };
  }

  if (pathname.startsWith("/suscribirse")) {
    return {
      activePath: "/suscribirse",
      backFallback: "/panel",
      breadcrumbs: [
        { href: "/panel", label: "Inicio" },
        { href: "/suscribirse", label: "Suscribirse" },
      ],
    };
  }

  if (pathname.startsWith("/panel")) {
    return {
      activePath: "/panel",
      backFallback: "/panel",
      breadcrumbs: [{ href: "/panel", label: "Inicio" }],
    };
  }

  return {
    activePath: "/",
    backFallback: "/",
    breadcrumbs: [{ href: "/", label: "EcoBrief Bolivia" }],
  };
};

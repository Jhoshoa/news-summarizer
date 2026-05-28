/* eslint-disable react-refresh/only-export-components */
import {
  type AnchorHTMLAttributes,
  createContext,
  type MouseEvent,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type RouterLocation = {
  pathname: string;
  search: string;
};

type RouterContextValue = {
  location: RouterLocation;
  back: (fallback?: string) => void;
  navigate: (to: string) => void;
  replace: (to: string) => void;
};

type LinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  "aria-label"?: string;
  href: string;
};

const RouterContext = createContext<RouterContextValue | null>(null);

const getCurrentLocation = (): RouterLocation => ({
  pathname: window.location.pathname,
  search: window.location.search,
});

const isInternalHref = (href: string) => {
  if (href.startsWith("#")) {
    return false;
  }

  try {
    const url = new URL(href, window.location.origin);
    return url.origin === window.location.origin;
  } catch {
    return false;
  }
};

const normalizeHref = (href: string) => {
  const url = new URL(href, window.location.origin);
  return `${url.pathname}${url.search}${url.hash}`;
};

export const RouterProvider = ({ children }: { children: ReactNode }) => {
  const [location, setLocation] = useState(getCurrentLocation);
  const [appHistoryIndex, setAppHistoryIndex] = useState(() => {
    const state = window.history.state as { appHistoryIndex?: number } | null;
    return state?.appHistoryIndex ?? 0;
  });

  useEffect(() => {
    const state = window.history.state as { appHistoryIndex?: number } | null;
    if (state?.appHistoryIndex === undefined) {
      window.history.replaceState(
        { ...(state ?? {}), appHistoryIndex: 0 },
        "",
        `${window.location.pathname}${window.location.search}${window.location.hash}`,
      );
    }
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      const state = window.history.state as { appHistoryIndex?: number } | null;
      setAppHistoryIndex(state?.appHistoryIndex ?? 0);
      setLocation(getCurrentLocation());
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((to: string) => {
    const next = normalizeHref(to);
    if (next === `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      return;
    }

    const nextIndex = appHistoryIndex + 1;
    window.history.pushState({ appHistoryIndex: nextIndex }, "", next);
    setAppHistoryIndex(nextIndex);
    setLocation(getCurrentLocation());
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [appHistoryIndex]);

  const replace = useCallback((to: string) => {
    const next = normalizeHref(to);
    window.history.replaceState({ appHistoryIndex }, "", next);
    setLocation(getCurrentLocation());
  }, [appHistoryIndex]);

  const back = useCallback(
    (fallback = "/") => {
      if (appHistoryIndex > 0) {
        window.history.back();
        return;
      }

      navigate(fallback);
    },
    [appHistoryIndex, navigate],
  );

  const value = useMemo(
    () => ({
      location,
      back,
      navigate,
      replace,
    }),
    [location, back, navigate, replace],
  );

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
};

export const useRouter = () => {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error("useRouter must be used inside RouterProvider");
  }
  return context;
};

export const Link = ({ children, className, href, target, ...props }: LinkProps) => {
  const { navigate } = useRouter();

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.altKey ||
      event.ctrlKey ||
      event.shiftKey ||
      target === "_blank" ||
      !isInternalHref(href)
    ) {
      return;
    }

    event.preventDefault();
    navigate(href);
  };

  return (
    <a className={className} href={href} target={target} onClick={handleClick} {...props}>
      {children}
    </a>
  );
};

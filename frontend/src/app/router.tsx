/* eslint-disable react-refresh/only-export-components */
import {
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
  navigate: (to: string) => void;
  replace: (to: string) => void;
};

type LinkProps = {
  children: ReactNode;
  className?: string;
  "aria-label"?: string;
  href: string;
  target?: string;
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

  useEffect(() => {
    const handlePopState = () => setLocation(getCurrentLocation());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((to: string) => {
    const next = normalizeHref(to);
    if (next === `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      return;
    }

    window.history.pushState(null, "", next);
    setLocation(getCurrentLocation());
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const replace = useCallback((to: string) => {
    const next = normalizeHref(to);
    window.history.replaceState(null, "", next);
    setLocation(getCurrentLocation());
  }, []);

  const value = useMemo(
    () => ({
      location,
      navigate,
      replace,
    }),
    [location, navigate, replace],
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

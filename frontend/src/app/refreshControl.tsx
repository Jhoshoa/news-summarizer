/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type RefreshControl = {
  isRefreshing: boolean;
  onRefresh?: () => void;
};

type RefreshControlContextValue = RefreshControl & {
  setRefreshControl: (control: RefreshControl) => void;
};

const RefreshControlContext = createContext<RefreshControlContextValue | null>(null);

const idleControl: RefreshControl = {
  isRefreshing: false,
};

export const RefreshControlProvider = ({ children }: { children: ReactNode }) => {
  const [control, setRefreshControl] = useState<RefreshControl>(idleControl);

  const value = useMemo(
    () => ({
      ...control,
      setRefreshControl,
    }),
    [control],
  );

  return (
    <RefreshControlContext.Provider value={value}>{children}</RefreshControlContext.Provider>
  );
};

export const useRefreshControlContext = () => {
  const context = useContext(RefreshControlContext);
  if (!context) {
    throw new Error("useRefreshControlContext must be used inside RefreshControlProvider");
  }
  return context;
};

export const usePageRefreshControl = (control: RefreshControl) => {
  const { setRefreshControl } = useRefreshControlContext();

  useEffect(() => {
    setRefreshControl(control);
    return () => setRefreshControl(idleControl);
  }, [control, setRefreshControl]);
};

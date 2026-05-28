import { memo } from "react";

import { Link } from "../../app/router";
import type { NavigationState } from "../../utils/navigation";
import { BoliviaFlag } from "./BoliviaFlag";

type HeaderProps = {
  activePath?: NavigationState["activePath"];
  compact?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void;
};

const HeaderComponent = ({
  activePath = "/",
  compact = false,
  isRefreshing = false,
  onRefresh,
}: HeaderProps) => (
  <header className={compact ? "topbar compact" : "topbar"}>
    <Link className="brand" href="/" aria-label="Noticias Bolivia IA inicio">
      <BoliviaFlag />
      <span>Noticias Bolivia IA</span>
    </Link>
    <nav className="nav" aria-label="Navegacion principal">
      <Link aria-current={activePath === "/news" || activePath === "/article" ? "page" : undefined} href="/news">
        Noticias
      </Link>
      <Link aria-current={activePath === "/datos" ? "page" : undefined} href="/datos">
        Datos
      </Link>
      <button className="button" type="button" onClick={onRefresh} disabled={isRefreshing}>
        {isRefreshing ? "Actualizando" : "Actualizar"}
      </button>
    </nav>
  </header>
);

export const Header = memo(HeaderComponent);

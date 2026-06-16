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
    <Link className="brand" href="/" aria-label="EcoBrief Bolivia inicio">
      <BoliviaFlag />
      <span>EcoBrief Bolivia</span>
      <span className="tz-indicator">Hora Bolivia</span>
    </Link>
    <nav className="nav" aria-label="Navegacion principal">
      <Link aria-current={activePath === "/news" || activePath === "/article" ? "page" : undefined} href="/news">
        Noticias
      </Link>
      <Link aria-current={activePath === "/datos" ? "page" : undefined} href="/datos">
        Datos
      </Link>
      <Link aria-current={activePath === "/impacto" ? "page" : undefined} href="/impacto">
        Impacto
      </Link>
      <Link aria-current={activePath === "/suscribirse" ? "page" : undefined} href="/suscribirse">
        Suscribirse
      </Link>
      {onRefresh && (
        <button className="button" type="button" onClick={onRefresh} disabled={isRefreshing}>
          {isRefreshing ? "Actualizando" : "Actualizar"}
        </button>
      )}
    </nav>
  </header>
);

export const Header = memo(HeaderComponent);

import { memo } from "react";

import { Link } from "../../app/router";
import { BoliviaFlag } from "./BoliviaFlag";

type HeaderProps = {
  compact?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void;
};

const HeaderComponent = ({ compact = false, isRefreshing = false, onRefresh }: HeaderProps) => (
  <header className={compact ? "topbar compact" : "topbar"}>
    <Link className="brand" href="/" aria-label="Noticias Bolivia IA inicio">
      <BoliviaFlag />
      <span>Noticias Bolivia IA</span>
    </Link>
    <nav className="nav" aria-label="Navegacion principal">
      <Link href="/news">Noticias</Link>
      <Link href="/datos">Datos</Link>
      <button className="button" type="button" onClick={onRefresh} disabled={isRefreshing}>
        {isRefreshing ? "Actualizando" : "Actualizar"}
      </button>
    </nav>
  </header>
);

export const Header = memo(HeaderComponent);

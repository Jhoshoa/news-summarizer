import { memo, useState } from "react";

import { Link } from "../../app/router";
import type { NavigationState } from "../../utils/navigation";
import { IconMenu, IconX } from "../icons/Icons";
import { BoliviaFlag } from "./BoliviaFlag";

type HeaderProps = {
  activePath?: NavigationState["activePath"];
  compact?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void;
};

const NAV_ITEMS: { href: string; label: string; match: NavigationState["activePath"][] }[] = [
  { href: "/", label: "Inicio", match: ["/"] },
  { href: "/news", label: "Noticias", match: ["/news", "/article"] },
  { href: "/datos", label: "Datos", match: ["/datos"] },
  { href: "/impacto", label: "Impacto", match: ["/impacto"] },
];

const HeaderComponent = ({
  activePath = "/",
  compact = false,
  isRefreshing = false,
  onRefresh,
}: HeaderProps) => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className={compact ? "topbar compact" : "topbar"}>
      <Link className="brand" href="/" aria-label="EcoBrief Bolivia inicio">
        <BoliviaFlag />
        <span>EcoBrief Bolivia</span>
      </Link>

      <nav className={menuOpen ? "nav open" : "nav"} aria-label="Navegacion principal">
        {NAV_ITEMS.map((item) => (
          <Link
            aria-current={item.match.includes(activePath) ? "page" : undefined}
            href={item.href}
            key={item.href}
            onClick={() => setMenuOpen(false)}
          >
            {item.label}
          </Link>
        ))}
        {onRefresh && (
          <button
            className="button nav-refresh"
            disabled={isRefreshing}
            onClick={onRefresh}
            type="button"
          >
            {isRefreshing ? "Actualizando" : "Actualizar"}
          </button>
        )}
        <Link className="button btn-sm nav-mobile-cta" href="/suscribirse" onClick={() => setMenuOpen(false)}>
          Suscribirme gratis
        </Link>
      </nav>

      <div className="nav-right">
        <span className="nav-clock">
          <span className="nav-clock-dot" />
          Hora Bolivia
        </span>
        <Link className="button btn-sm nav-cta" href="/suscribirse">
          Suscribirme
        </Link>
        <button
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Cerrar menu" : "Abrir menu"}
          className="nav-toggle"
          onClick={() => setMenuOpen((open) => !open)}
          type="button"
        >
          {menuOpen ? <IconX size={20} /> : <IconMenu size={20} />}
        </button>
      </div>
    </header>
  );
};

export const Header = memo(HeaderComponent);

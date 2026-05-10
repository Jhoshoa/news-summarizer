import { BoliviaFlag } from "./BoliviaFlag";

type HeaderProps = {
  compact?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void;
};

export const Header = ({ compact = false, isRefreshing = false, onRefresh }: HeaderProps) => (
  <header className="topbar">
    <a className="brand" href="/" aria-label="Noticias Bolivia IA inicio">
      <BoliviaFlag />
      <span>Noticias Bolivia IA</span>
    </a>
    <nav className="nav" aria-label="Navegacion principal">
      <a href="#ultimo">Ultimo</a>
      <a href="/news">Noticias</a>
      <a href="/datos">Datos</a>
      {!compact && <a href="#departamentos">Departamentos</a>}
      <button className="button" type="button" onClick={onRefresh} disabled={isRefreshing}>
        {isRefreshing ? "Actualizando" : "Actualizar"}
      </button>
    </nav>
  </header>
);

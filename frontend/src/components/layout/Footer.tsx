import { memo } from "react";

import { Link } from "../../app/router";

const FooterComponent = () => (
  <footer className="footer">
    <div className="footer-links">
      <span>EcoBrief Lab</span>
      <Link href="/impacto#fuentes">Fuentes</Link>
      <Link href="/news">Archivo</Link>
      <Link href="/impacto#politica-editorial">Politica editorial</Link>
    </div>
    <span className="footer-note">Eficiencia informativa sin claims de CO2 o kWh.</span>
  </footer>
);

export const Footer = memo(FooterComponent);

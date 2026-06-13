import { memo } from "react";

import { Link } from "../../app/router";

const FooterComponent = () => (
  <footer className="footer">
    <div className="footer-links">
      <span>EcoBrief Lab</span>
      <Link href="/fuentes">Fuentes</Link>
    </div>
  </footer>
);

export const Footer = memo(FooterComponent);

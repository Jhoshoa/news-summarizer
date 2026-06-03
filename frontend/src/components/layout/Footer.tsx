import { memo } from "react";

const FooterComponent = () => (
  <footer className="footer">
    <div className="footer-links">
      <span>EcoBrief Lab</span>
      <a href="#fuentes">Fuentes</a>
      <a href="#archivo">Archivo</a>
      <a href="#politica-editorial">Politica editorial</a>
      <a href="#contacto">Contacto</a>
    </div>
    <div className="socials" aria-label="Redes sociales">
      <a className="social" href="#facebook" aria-label="Facebook">
        f
      </a>
      <a className="social" href="#instagram" aria-label="Instagram">
        ig
      </a>
      <a className="social" href="#tiktok" aria-label="TikTok">
        tk
      </a>
      <a className="social" href="#x" aria-label="X">
        X
      </a>
    </div>
  </footer>
);

export const Footer = memo(FooterComponent);

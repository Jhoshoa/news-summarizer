import type { Article } from "../../services/types";
import type { WeatherResponse } from "../../services/types";

type PhoneBriefProps = {
  headline: string;
  articles: Article[];
  p2pBuy?: string;
  p2pSell?: string;
  weather?: WeatherResponse;
};

export const PhoneBrief = ({ headline, articles, p2pBuy = "--", p2pSell = "--", weather }: PhoneBriefProps) => {
  const leadItems = articles.slice(0, 2);
  const city = weather?.location.name ?? "La Paz";
  const temp = weather?.current.temperature_2m ? `${Math.round(Number(weather.current.temperature_2m))}C` : "--";
  const uv = weather?.radiation.uv_index ?? weather?.today.uv_index_max;

  return (
    <aside className="phone-brief" aria-label="Resumen movil">
      <div className="phone-screen">
        <span className="pill">Resumen del dia</span>
        <h2>{headline}</h2>
        <p>Vista rapida para usuarios moviles: titulares, indicadores y alertas locales.</p>

        <div className="brief-block">
          <strong>Ultima hora</strong>
          {leadItems.map((article) => (
            <span key={article.id}>{article.title}</span>
          ))}
        </div>

        <div className="brief-block">
          <strong>Dolar P2P</strong>
          <span>
            Compra Bs {p2pBuy} - Venta Bs {p2pSell}
          </span>
        </div>

        <div className="brief-block">
          <strong>Clima {city}</strong>
          <span>
            {temp}: Radiacion UV {uv ?? "--"}
          </span>
        </div>

        <div className="brief-block">
          <strong>Transito</strong>
          <span>18 alertas en la red vial nacional</span>
        </div>
      </div>
    </aside>
  );
};

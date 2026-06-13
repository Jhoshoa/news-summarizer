import type { WeatherResponse } from "../../services/types";

type WeatherPanelProps = {
  weather?: WeatherResponse;
};

const formatWeatherValue = (value?: number | null, suffix = "") => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "--";
  }

  return `${Math.round(value)}${suffix}`;
};

export const WeatherPanel = ({ weather }: WeatherPanelProps) => {
  const city = weather?.location.name ?? "La Paz";
  const temp = Number(weather?.current.temperature_2m);
  const uv = weather?.today.uv_index_max;

  return (
    <section className="weather-card" id="clima" aria-label="Clima local">
      <div className="panel-title">Clima local</div>
      <div className="weather-row">
        <div>
          <strong>{city}</strong>
          <span>Radiacion UV {formatWeatherValue(uv)}</span>
        </div>
        <b>{formatWeatherValue(temp, "C")}</b>
      </div>
    </section>
  );
};

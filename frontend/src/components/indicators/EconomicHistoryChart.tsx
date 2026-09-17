import { createChart, CrosshairMode, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";

import { useGetEconomicIndicatorsHistoryQuery } from "../../services/api";
import { formatNumber } from "./indicatorUtils";

const OFICIAL_CODE = "bcb_tipo_de_cambio_oficial";
const COMPRA_CODE = "binance_p2p_usdt_bob_buy";
const VENTA_CODE = "binance_p2p_usdt_bob_sell";

const COLOR_OFICIAL = "#006d77";
const COLOR_COMPRA = "#16a34a";
const COLOR_VENTA = "#a94138";

type RangeKey = "1" | "7" | "30" | "90" | "all";
const RANGES: Array<{ key: RangeKey; label: string }> = [
  { key: "1", label: "1D" },
  { key: "7", label: "7D" },
  { key: "30", label: "1M" },
  { key: "90", label: "3M" },
  { key: "all", label: "Todo" },
];

// Cuanto pedirle al backend por cada rango -- antes se pedian siempre 180
// dias sin importar el boton activo y el recorte era solo visual (setVisibleRange
// sobre el mismo dataset gigante), asi que cada carga bajaba y parseaba miles
// de puntos (el par de Binance se recolecta cada 30 min) aunque solo se
// fueran a mostrar los ultimos 7 dias. Ahora cada rango pide solo lo suyo.
// "all" usa 365 porque es el maximo que el backend acepta (MAX_HISTORY_DAYS
// en src/api/economic_indicators.py); alcanza de sobra dado el historico real.
const RANGE_DAYS: Record<RangeKey, number> = { "1": 1, "7": 7, "30": 30, "90": 90, all: 365 };

type Point = { time: UTCTimestamp; value: number };

// El backend manda collected_at como hora de Bolivia "naive" (sin offset, ej.
// "2026-09-16T21:00:00" -- ver _now_bolivia en src/db/repository.py). Lightweight
// Charts SIEMPRE arma las etiquetas del eje con los getters UTC del Date que le
// pases (getUTCFullYear/getUTCHours/etc, es como esta hecha la libreria). Si en
// vez de esto se hace `new Date(collected_at).getTime()`, el navegador interpreta
// ese string sin offset como su propia hora LOCAL -- en Bolivia eso da el epoch
// UTC correcto, pero el grafico despues lo vuelve a mostrar con los getters UTC,
// sumando 4 horas de mas y empujando todo a "manana" pasado cierta hora. La
// solucion es tomar los numeros de Bolivia tal cual y meterlos directo como si
// fueran UTC (Date.UTC), sin dejar que el navegador haga ninguna conversion de
// huso horario -- asi el eje siempre muestra la hora de Bolivia real, sin
// importar en que huso horario este el navegador de quien mira el grafico.
export const parseBoliviaTimestamp = (value: string): number => {
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/);
  if (!match) return Math.floor(new Date(value).getTime() / 1000);
  const [, year, month, day, hour, minute, second] = match.map(Number);
  return Math.floor(Date.UTC(year, month - 1, day, hour, minute, second) / 1000);
};

const toSeriesPoints = (rows: Array<{ value: number; collected_at: string }> | undefined): Point[] => {
  if (!rows || rows.length === 0) return [];
  const byTime = new Map<number, number>();
  for (const row of rows) {
    const t = parseBoliviaTimestamp(row.collected_at);
    byTime.set(t, row.value);
  }
  return Array.from(byTime.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([time, value]) => ({ time: time as UTCTimestamp, value }));
};

const fmtBs = (value: number | null | undefined) => (value == null ? "—" : `Bs ${formatNumber(value, 2)}`);

export const EconomicHistoryChart = () => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<Record<string, ISeriesApi<"Line">>>({});
  const [range, setRange] = useState<RangeKey>("7");

  // data cae en el ultimo resultado exitoso (aunque sea de un rango
  // distinto al actual) mientras el nuevo rango todavia esta cargando --
  // asi el grafico sigue mostrando lo anterior en vez de irse a blanco al
  // cambiar de boton, e isFetching sirve para mostrar un indicador chico.
  const { data, isFetching } = useGetEconomicIndicatorsHistoryQuery({
    codes: [OFICIAL_CODE, COMPRA_CODE, VENTA_CODE],
    days: RANGE_DAYS[range],
  });

  const oficialPoints = useMemo(() => toSeriesPoints(data?.series[OFICIAL_CODE]), [data]);
  const compraPoints = useMemo(() => toSeriesPoints(data?.series[COMPRA_CODE]), [data]);
  const ventaPoints = useMemo(() => toSeriesPoints(data?.series[VENTA_CODE]), [data]);

  const lastOficial = oficialPoints[oficialPoints.length - 1]?.value ?? null;
  const lastCompra = compraPoints[compraPoints.length - 1]?.value ?? null;
  const lastVenta = ventaPoints[ventaPoints.length - 1]?.value ?? null;
  const gap = lastOficial != null && lastVenta != null ? lastVenta - lastOficial : null;
  const gapPct = gap != null && lastOficial ? (gap / lastOficial) * 100 : null;

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#ffffff" }, textColor: "#666666", fontFamily: "Inter, sans-serif", fontSize: 11 },
      grid: { vertLines: { color: "#f0f1f3" }, horzLines: { color: "#f0f1f3" } },
      rightPriceScale: { borderColor: "rgba(34,34,34,0.12)" },
      timeScale: { borderColor: "rgba(34,34,34,0.12)", timeVisible: true, secondsVisible: false },
      crosshair: { mode: CrosshairMode.Normal },
      handleScroll: true,
      handleScale: true,
      width: containerRef.current.clientWidth,
      height: 320,
    });

    seriesRef.current.oficial = chart.addLineSeries({
      color: COLOR_OFICIAL,
      lineWidth: 3,
      pointMarkersVisible: true,
      pointMarkersRadius: 4,
      priceLineVisible: false,
      lastValueVisible: true,
      title: "Oficial",
    });
    seriesRef.current.compra = chart.addLineSeries({
      color: COLOR_COMPRA,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: "Compra",
    });
    seriesRef.current.venta = chart.addLineSeries({
      color: COLOR_VENTA,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: "Venta",
    });

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    chartRef.current = chart;
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = {};
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    seriesRef.current.oficial?.setData(oficialPoints);
    seriesRef.current.compra?.setData(compraPoints);
    seriesRef.current.venta?.setData(ventaPoints);
    chartRef.current.timeScale().fitContent();
  }, [oficialPoints, compraPoints, ventaPoints]);

  return (
    <section className="data-panel economic-history-panel">
      <div className="panel-heading">
        <span className="panel-title">Historico del dolar</span>
        <div className="chart-range-controls">
          {isFetching && (oficialPoints.length > 0 || compraPoints.length > 0) && (
            <span className="chart-range-updating">Actualizando...</span>
          )}
          <div className="chart-range-buttons" role="group" aria-label="Rango de fechas">
            {RANGES.map((r) => (
              <button
                key={r.key}
                type="button"
                className={r.key === range ? "active" : ""}
                onClick={() => setRange(r.key)}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="chart-stat-row">
        <div className="chart-stat">
          <span className="chart-swatch" style={{ background: COLOR_OFICIAL }} />
          <div>
            <span>Oficial BCB</span>
            <strong>{fmtBs(lastOficial)}</strong>
          </div>
        </div>
        <div className="chart-stat">
          <span className="chart-swatch" style={{ background: COLOR_COMPRA }} />
          <div>
            <span>Binance compra</span>
            <strong>{fmtBs(lastCompra)}</strong>
          </div>
        </div>
        <div className="chart-stat">
          <span className="chart-swatch" style={{ background: COLOR_VENTA }} />
          <div>
            <span>Binance venta</span>
            <strong>{fmtBs(lastVenta)}</strong>
          </div>
        </div>
        <div className="chart-stat">
          <div>
            <span>Brecha vs. oficial</span>
            <strong>{gap == null ? "—" : `${gap >= 0 ? "+" : ""}Bs ${formatNumber(gap, 2)}`}</strong>
            {gapPct != null && (
              <small>
                {gapPct >= 0 ? "+" : ""}
                {formatNumber(gapPct, 1)}% sobre el oficial
              </small>
            )}
          </div>
        </div>
      </div>

      <div ref={containerRef} className="chart-canvas" />

      {isFetching && oficialPoints.length === 0 && compraPoints.length === 0 && (
        <p className="chart-loading-note">Cargando historico...</p>
      )}
      <p className="chart-footnote">
        Datos reales de produccion, actualizados cada 10 minutos. El oficial cambia con poca frecuencia; el paralelo
        se recalcula seguido.
      </p>
    </section>
  );
};

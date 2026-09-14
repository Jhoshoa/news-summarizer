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

type RangeKey = "7" | "30" | "90" | "all";
const RANGES: Array<{ key: RangeKey; label: string }> = [
  { key: "7", label: "7D" },
  { key: "30", label: "1M" },
  { key: "90", label: "3M" },
  { key: "all", label: "Todo" },
];

type Point = { time: UTCTimestamp; value: number };

const toSeriesPoints = (rows: Array<{ value: number; collected_at: string }> | undefined): Point[] => {
  if (!rows || rows.length === 0) return [];
  const byTime = new Map<number, number>();
  for (const row of rows) {
    const t = Math.floor(new Date(row.collected_at).getTime() / 1000);
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
  const [range, setRange] = useState<RangeKey>("30");
  const [hover, setHover] = useState<{ oficial: number | null; compra: number | null; venta: number | null } | null>(
    null,
  );

  const { data, isFetching } = useGetEconomicIndicatorsHistoryQuery({
    codes: [OFICIAL_CODE, COMPRA_CODE, VENTA_CODE],
    days: 180,
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

    chart.subscribeCrosshairMove((param) => {
      if (!param.time) {
        setHover(null);
        return;
      }
      const o = param.seriesData.get(seriesRef.current.oficial) as { value: number } | undefined;
      const c = param.seriesData.get(seriesRef.current.compra) as { value: number } | undefined;
      const v = param.seriesData.get(seriesRef.current.venta) as { value: number } | undefined;
      setHover({ oficial: o?.value ?? null, compra: c?.value ?? null, venta: v?.value ?? null });
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

  useEffect(() => {
    if (!chartRef.current) return;
    if (range === "all") {
      chartRef.current.timeScale().fitContent();
      return;
    }
    const allPoints = [...compraPoints, ...oficialPoints];
    if (allPoints.length === 0) return;
    const maxTime = Math.max(...allPoints.map((p) => p.time));
    const minTime = Math.min(...allPoints.map((p) => p.time));
    const days = parseInt(range, 10);
    const from = Math.max(maxTime - days * 86400, minTime);
    chartRef.current.timeScale().setVisibleRange({ from: from as UTCTimestamp, to: maxTime as UTCTimestamp });
  }, [range, compraPoints, oficialPoints]);

  const displayOficial = hover ? hover.oficial : lastOficial;
  const displayCompra = hover ? hover.compra : lastCompra;
  const displayVenta = hover ? hover.venta : lastVenta;

  return (
    <section className="data-panel economic-history-panel">
      <div className="panel-heading">
        <span className="panel-title">Historico del dolar</span>
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

      <div className="chart-stat-row">
        <div className="chart-stat">
          <span className="chart-swatch" style={{ background: COLOR_OFICIAL }} />
          <div>
            <span>Oficial BCB</span>
            <strong>{fmtBs(displayOficial)}</strong>
          </div>
        </div>
        <div className="chart-stat">
          <span className="chart-swatch" style={{ background: COLOR_COMPRA }} />
          <div>
            <span>Binance compra</span>
            <strong>{fmtBs(displayCompra)}</strong>
          </div>
        </div>
        <div className="chart-stat">
          <span className="chart-swatch" style={{ background: COLOR_VENTA }} />
          <div>
            <span>Binance venta</span>
            <strong>{fmtBs(displayVenta)}</strong>
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

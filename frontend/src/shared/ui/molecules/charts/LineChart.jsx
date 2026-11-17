import { useId, useState } from "react";
import styles from "./LineChart.module.css";

const W = 640;
const H = 240;
const M = { top: 12, right: 16, bottom: 28, left: 52 };

/** Estilo de cada serie: color + trazo, para no depender solo del color. */
const SERIES_STYLE = {
  avg: { cls: "s1", dash: "" },
  max: { cls: "s2", dash: "6 4" },
  min: { cls: "s3", dash: "2 4" },
  raw: { cls: "s4", dash: "", markersOnly: true },
};

const formatTime = (ms) =>
  new Date(ms).toLocaleString("es", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const formatNumber = (value) => (Number.isInteger(value) ? String(value) : value.toFixed(2));

/**
 * Gráfica de líneas genérica en SVG. `series` es una lista de { id, label, points: [{ x: ms, y }] }.
 * `band` ({ min, max }) sombrea el rango normal. Al pasar el cursor muestra el punto más cercano.
 * Con más de una serie muestra leyenda. `unit` solo se usa para rotular valores.
 */
function LineChart({ series, unit = "", band = null, title }) {
  const titleId = useId();
  const [hover, setHover] = useState(null);

  const points = series.flatMap((s) => s.points);
  if (points.length === 0) return <p className={styles.empty}>Sin datos.</p>;

  let xMin = Math.min(...points.map((p) => p.x));
  let xMax = Math.max(...points.map((p) => p.x));
  if (xMin === xMax) {
    xMin -= 30 * 60_000;
    xMax += 30 * 60_000;
  }
  const ys = points.map((p) => p.y);
  if (band) ys.push(band.min ?? Infinity, band.max ?? -Infinity);
  let yMin = Math.min(...ys.filter(Number.isFinite));
  let yMax = Math.max(...ys.filter(Number.isFinite));
  if (yMin === yMax) {
    yMin -= 1;
    yMax += 1;
  }
  const pad = (yMax - yMin) * 0.08;
  yMin -= pad;
  yMax += pad;

  const px = (x) => M.left + ((x - xMin) / (xMax - xMin)) * (W - M.left - M.right);
  const py = (y) => H - M.bottom - ((y - yMin) / (yMax - yMin)) * (H - M.top - M.bottom);

  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + ((yMax - yMin) * i) / 4);
  const xTicks = Array.from({ length: 4 }, (_, i) => xMin + ((xMax - xMin) * i) / 3);

  const handleMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = xMin + ((event.clientX - rect.left) / rect.width) * (xMax - xMin);
    let best = null;
    for (const s of series) {
      for (const p of s.points) {
        const distance = Math.abs(p.x - x);
        if (!best || distance < best.distance) best = { distance, point: p, series: s };
      }
    }
    setHover(best);
  };

  return (
    <figure className={styles.chart}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={titleId} className={styles.svg}>
        <title id={titleId}>{title}</title>

        {band && band.min != null && band.max != null && (
          <rect
            className={styles.band}
            x={M.left}
            width={W - M.left - M.right}
            y={py(band.max)}
            height={Math.max(0, py(band.min) - py(band.max))}
          />
        )}

        {yTicks.map((tick) => (
          <g key={tick}>
            <line className={styles.grid} x1={M.left} x2={W - M.right} y1={py(tick)} y2={py(tick)} />
            <text className={styles.tick} x={M.left - 8} y={py(tick)} textAnchor="end" dominantBaseline="middle">
              {formatNumber(tick)}
            </text>
          </g>
        ))}
        {xTicks.map((tick) => (
          <text key={tick} className={styles.tick} x={px(tick)} y={H - 8} textAnchor="middle">
            {formatTime(tick)}
          </text>
        ))}

        {series.map((s) => {
          const style = SERIES_STYLE[s.id] ?? SERIES_STYLE.avg;
          return (
            <g key={s.id} className={styles[style.cls]}>
              {!style.markersOnly && s.points.length > 1 && (
                <polyline
                  className={styles.line}
                  strokeDasharray={style.dash}
                  points={s.points.map((p) => `${px(p.x)},${py(p.y)}`).join(" ")}
                />
              )}
              {(style.markersOnly || s.points.length === 1 || s.points.length <= 24) &&
                s.points.map((p) => (
                  <circle key={p.x} className={styles.dot} cx={px(p.x)} cy={py(p.y)} r={style.markersOnly ? 4 : 3} />
                ))}
            </g>
          );
        })}

        {hover && (
          <g pointerEvents="none">
            <line className={styles.cursor} x1={px(hover.point.x)} x2={px(hover.point.x)} y1={M.top} y2={H - M.bottom} />
            <circle
              className={`${styles.focus} ${styles[(SERIES_STYLE[hover.series.id] ?? SERIES_STYLE.avg).cls]}`}
              cx={px(hover.point.x)}
              cy={py(hover.point.y)}
              r="6"
            />
          </g>
        )}

        <rect
          x={M.left}
          y={M.top}
          width={W - M.left - M.right}
          height={H - M.top - M.bottom}
          fill="transparent"
          onMouseMove={handleMove}
          onMouseLeave={() => setHover(null)}
        />
      </svg>

      {hover && (
        <div
          className={styles.tooltip}
          style={{ left: `${(px(hover.point.x) / W) * 100}%`, top: `${(py(hover.point.y) / H) * 100}%` }}
        >
          <strong>
            {formatNumber(hover.point.y)} {unit}
          </strong>
          <span>{hover.series.label}</span>
          <span>{formatTime(hover.point.x)}</span>
        </div>
      )}

      {series.length > 1 && (
        <figcaption className={styles.legend}>
          {series.map((s) => {
            const style = SERIES_STYLE[s.id] ?? SERIES_STYLE.avg;
            return (
              <span key={s.id} className={`${styles.legendItem} ${styles[style.cls]}`}>
                <svg width="22" height="10" aria-hidden="true">
                  {style.markersOnly ? (
                    <circle cx="11" cy="5" r="4" className={styles.swatchFill} />
                  ) : (
                    <line x1="0" x2="22" y1="5" y2="5" className={styles.swatchLine} strokeDasharray={style.dash} />
                  )}
                </svg>
                {s.label}
              </span>
            );
          })}
        </figcaption>
      )}
    </figure>
  );
}

export default LineChart;

"use client";

import { forwardRef } from "react";
import type { Assignment, FoldFile } from "@/lib/api";

const STYLE: Record<Assignment, { stroke: string; dash?: string; width: number }> = {
  M: { stroke: "var(--mountain)", dash: "0.03 0.012 0.006 0.012", width: 0.008 },
  V: { stroke: "var(--valley)", dash: "0.025 0.014", width: 0.008 },
  B: { stroke: "var(--ink)", width: 0.012 },
  F: { stroke: "var(--flat)", width: 0.004 },
  U: { stroke: "var(--muted)", width: 0.006 },
};

// Paint order: flat precreases under folds, the border on top.
const ORDER: Assignment[] = ["F", "U", "V", "M", "B"];

interface Props {
  fold: FoldFile;
  labels?: { corner: [number, number]; part: string }[];
  title?: string;
  size?: number;
}

/** Renders a FOLD crease pattern (unit square, origin bottom-left) as SVG. */
export const CreasePattern = forwardRef<SVGSVGElement, Props>(function CreasePattern(
  { fold, labels = [], title, size },
  ref,
) {
  const pad = labels.length ? 0.16 : 0.03;
  const v = fold.vertices_coords;
  const edges = fold.edges_vertices
    .map((e, i) => ({ a: v[e[0]], b: v[e[1]], t: fold.edges_assignment[i] ?? "U" }))
    .sort((x, y) => ORDER.indexOf(x.t) - ORDER.indexOf(y.t));

  return (
    <svg
      ref={ref}
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`${-pad} ${-pad} ${1 + 2 * pad} ${1 + 2 * pad}`}
      width={size}
      height={size}
      role="img"
      aria-label={title ?? fold.frame_title ?? "Crease pattern"}
      className="cp"
    >
      <title>{title ?? fold.frame_title ?? "Crease pattern"}</title>
      <rect x={0} y={0} width={1} height={1} fill="var(--paper)" />
      {edges.map((e, i) => {
        const s = STYLE[e.t] ?? STYLE.U;
        return (
          <line
            key={i}
            x1={e.a[0]}
            y1={1 - e.a[1]}
            x2={e.b[0]}
            y2={1 - e.b[1]}
            stroke={s.stroke}
            strokeWidth={s.width}
            strokeDasharray={s.dash}
            strokeLinecap="round"
          />
        );
      })}
      {labels.map((l, i) => {
        const [cx, cy] = l.corner;
        const x = cx === 0 ? -0.02 : 1.02;
        const y = 1 - cy + (cy === 0 ? 0.075 : -0.045);
        return (
          <g key={i}>
            <circle cx={cx} cy={1 - cy} r={0.018} fill="var(--accent)" />
            <text
              x={x}
              y={y}
              fontSize={0.05}
              textAnchor={cx === 0 ? "start" : "end"}
              fill="var(--ink)"
              fontFamily="system-ui, sans-serif"
            >
              {l.part}
            </text>
          </g>
        );
      })}
    </svg>
  );
});

export function Legend() {
  return (
    <ul className="legend">
      <li><span className="swatch m" /> Mountain</li>
      <li><span className="swatch v" /> Valley</li>
      <li><span className="swatch f" /> Precrease (flat)</li>
      <li><span className="swatch b" /> Edge</li>
    </ul>
  );
}

/** Serialise an on-screen crease pattern to a standalone SVG file, resolving CSS colour variables. */
export function svgToFile(svg: SVGSVGElement): string {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  const styles = getComputedStyle(svg);
  const resolve = (val: string | null) =>
    val?.replace(/var\((--[a-z-]+)\)/g, (_, name) => styles.getPropertyValue(name).trim() || "#000") ?? null;
  clone.querySelectorAll("*").forEach((el) => {
    for (const attr of ["stroke", "fill"]) {
      const v = el.getAttribute(attr);
      if (v?.includes("var(")) el.setAttribute(attr, resolve(v)!);
    }
  });
  clone.setAttribute("width", "800");
  clone.setAttribute("height", "800");
  return `<?xml version="1.0" encoding="UTF-8"?>\n${clone.outerHTML}`;
}

from __future__ import annotations

CANVAS_CSS = r"""
  #graphCanvas {
    position: fixed; inset: 0; width: 100vw; height: 100vh;
    z-index: 1; cursor: grab; display: block;
  }
  #graphCanvas:active { cursor: grabbing; }
  #graphCanvas.kp-hover { cursor: pointer; }

  .coord-hud {
    position: fixed; right: 16px; bottom: 16px; z-index: 9;
    border-radius: 11px; padding: 6px 11px; font-family: var(--font-mono); font-size: 11.5px;
    color: var(--muted-foreground); display: flex; align-items: center; gap: 10px;
    pointer-events: none; transition: opacity 0.18s ease;
  }
  .coord-hud.hidden { opacity: 0; }
  .coord-hud span strong { color: var(--foreground); font-weight: 500; }

  .trace-pill {
    position: fixed; z-index: 12; pointer-events: none;
    padding: 5px 10px; border-radius: 10px; font-size: 12px; white-space: nowrap;
    opacity: 0; transform: translate(-50%, -138%); transition: opacity 0.1s ease;
    display: inline-flex; align-items: center; gap: 8px;
  }
  .trace-pill.visible { opacity: 1; }
  .trace-badge {
    font-size: 10px; font-weight: 500; letter-spacing: 0.02em;
    padding: 1.5px 6px; border-radius: 6px;
    background: var(--secondary); color: var(--muted-foreground);
  }
"""

CANVAS_HTML = r"""
  <canvas id="graphCanvas"></canvas>
  <div id="coordHud" class="liquid-glass coord-hud">
    <span>x <strong id="hudX">0.00</strong></span>
    <span>y <strong id="hudY">0.00</strong></span>
    <span style="opacity:0.45">|</span>
    <span id="hudZoom">1.0×</span>
  </div>
  <div id="tracePill" class="liquid-glass trace-pill"></div>
"""

CANVAS_JS = r"""
  const KP_LABELS = {
    root: "Nullstelle",
    extrema: "Extremum",
    intersection: "Schnittpunkt",
    intercept: "y-Achse",
    point: "Punkt",
  };

  let hoveredKeyPoint = null;
  let pinnedKeyPoints = [];
  const cam3D = { yaw: 0.68, pitch: 0.52, zoom: 1.0 };

  function getExprStyle(ex) {
    const baseWidth = ex.lineWidth ?? (ex.id === activeExprId ? 2.8 : 2.2);
    const opacity = ex.opacity ?? 1.0;
    const style = ex.lineStyle || "solid";
    let dash = [];
    if (style === "dashed") dash = [8, 6];
    else if (style === "dotted") dash = [2.2, 5.5];
    return { width: baseWidth, opacity, style, dash };
  }

  function niceStep(rawStep) {
    if (!Number.isFinite(rawStep) || rawStep <= 0) return 1;
    const exp = Math.floor(Math.log10(rawStep));
    const pow = Math.pow(10, exp);
    if (!Number.isFinite(pow) || pow <= 0) return rawStep;
    const norm = rawStep / pow;
    if (norm < 1.5) return 1 * pow;
    if (norm < 3.5) return 2 * pow;
    if (norm < 7.5) return 5 * pow;
    return 10 * pow;
  }

  function formatTick(val, isPi, step) {
    if (Math.abs(val) < step * 1e-6) return "0";
    if (isPi && Math.abs(val) < 1e7) {
      const k = Math.round((val / (Math.PI / 2)) * 100) / 100;
      if (Math.abs(k - Math.round(k)) < 1e-3) {
        const n = Math.round(k);
        if (n % 2 === 0) {
          const m = n / 2;
          if (m === 1) return "π";
          if (m === -1) return "−π";
          return `${m}π`.replace("-", "−");
        }
        if (n === 1) return "π/2";
        if (n === -1) return "−π/2";
        return `${n}π/2`.replace("-", "−");
      }
    }
    const abs = Math.abs(val);
    if (abs >= 1e6 || abs < 1e-4) {
      const s = val.toExponential(2);
      const [mant, expStr] = s.split("e");
      const cleanMant = String(Number(mant));
      const cleanExp = expStr.replace("+", "");
      return `${cleanMant}e${cleanExp}`.replace(/-/g, "−");
    }
    return String(Number(val.toPrecision(6))).replace("-", "−");
  }

  function getGridSteps() {
    const stepY = niceStep(88 / view.scale);
    let stepX = stepY;
    if (piMode) {
      const target = 88 / view.scale;
      const base = Math.PI / 2;
      const mult = Math.pow(2, Math.round(Math.log2(Math.max(target / base, 1e-12))));
      if (Number.isFinite(base * mult) && base * mult > 0) stepX = base * mult;
    }
    return { stepX, stepY };
  }

  function drawPolarGrid(colMinor, colMajor, colAxis, colLabel) {
    const ax = worldToScreenX(0);
    const ay = worldToScreenY(0);
    if (!Number.isFinite(ax) || !Number.isFinite(ay)) return;

    const rStep = niceStep(92 / view.scale);
    if (!Number.isFinite(rStep) || rStep <= 0) return;

    const corners = [[0, 0], [width, 0], [0, height], [width, height]];
    let maxPixR = 0;
    let minPixR = Infinity;
    for (const [cx, cy] of corners) {
      const d = Math.hypot(cx - ax, cy - ay);
      if (d > maxPixR) maxPixR = d;
      if (d < minPixR) minPixR = d;
    }
    if (ax >= 0 && ax <= width && ay >= 0 && ay <= height) minPixR = 0;

    const maxWorldR = maxPixR / view.scale;
    const minWorldR = Math.max(0, minPixR / view.scale);
    const kStart = Math.max(1, Math.floor(minWorldR / rStep));
    const kEnd = Math.min(kStart + 80, Math.ceil(maxWorldR / rStep));

    if (settings.showGrid) {
      ctx.strokeStyle = colMinor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let k = kStart; k <= kEnd; k++) {
        const pr = (k - 0.5) * rStep * view.scale;
        if (pr > 4 && pr < 1e6) {
          ctx.moveTo(ax + pr, ay);
          ctx.arc(ax, ay, pr, 0, Math.PI * 2);
        }
      }
      ctx.stroke();

      ctx.strokeStyle = colMajor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let k = kStart; k <= kEnd; k++) {
        const pr = k * rStep * view.scale;
        if (pr > 4 && pr < 1e6) {
          ctx.moveTo(ax + pr, ay);
          ctx.arc(ax, ay, pr, 0, Math.PI * 2);
        }
      }
      const rayLen = Math.min(maxPixR + 40, 20000);
      for (let a = 0; a < 12; a++) {
        const ang = (a * Math.PI) / 6;
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax + Math.cos(ang) * rayLen, ay - Math.sin(ang) * rayLen);
      }
      ctx.stroke();
    }

    ctx.strokeStyle = colAxis;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    if (ax >= 0 && ax <= width) { ctx.moveTo(ax, 0); ctx.lineTo(ax, height); }
    if (ay >= 0 && ay <= height) { ctx.moveTo(0, ay); ctx.lineTo(width, ay); }
    ctx.stroke();

    if (settings.showAxisLabels) {
      ctx.fillStyle = colLabel;
      ctx.font = '500 11px "Roboto Mono", ui-monospace, monospace';
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const labelY = Math.min(Math.max(ay + 7, 10), height - 22);
      for (let k = kStart; k <= kEnd; k++) {
        const r = k * rStep;
        const sx = ax + r * view.scale;
        if (sx > 28 && sx < width - 28) ctx.fillText(formatTick(r, false, rStep), sx, labelY);
      }

      const ringR = Math.min(Math.max(120, Math.min(width, height) * 0.36), maxPixR * 0.85);
      const angleLabels = ["0", "π/6", "π/3", "π/2", "2π/3", "5π/6", "π", "7π/6", "4π/3", "3π/2", "5π/3", "11π/6"];
      ctx.textBaseline = "middle";
      for (let a = 1; a < 12; a++) {
        if (a === 6) continue;
        const ang = (a * Math.PI) / 6;
        const lx = ax + Math.cos(ang) * ringR;
        const ly = ay - Math.sin(ang) * ringR;
        if (lx > 24 && lx < width - 24 && ly > 18 && ly < height - 18) {
          ctx.fillText(angleLabels[a], lx, ly);
        }
      }
    }
  }

  function drawGrid() {
    const cs = getComputedStyle(document.documentElement);
    const colMinor = cs.getPropertyValue("--grid-minor").trim();
    const colMajor = cs.getPropertyValue("--grid-major").trim();
    const colAxis = cs.getPropertyValue("--grid-axis").trim();
    const colLabel = cs.getPropertyValue("--grid-label").trim();

    if (settings.polarGrid) {
      drawPolarGrid(colMinor, colMajor, colAxis, colLabel);
      return;
    }

    const bounds = getBounds();
    const { stepX, stepY } = getGridSteps();
    if (!Number.isFinite(stepX) || stepX <= 0 || !Number.isFinite(stepY) || stepY <= 0) return;

    const drawVLines = (step) => {
      const i0 = Math.floor(bounds.xmin / step);
      const i1 = Math.ceil(bounds.xmax / step);
      if (!Number.isFinite(i0) || !Number.isFinite(i1) || i1 - i0 > 400) return;
      for (let i = i0; i <= i1; i++) {
        const sx = Math.round(worldToScreenX(i * step)) + 0.5;
        if (sx >= -2 && sx <= width + 2) { ctx.moveTo(sx, 0); ctx.lineTo(sx, height); }
      }
    };

    const drawHLines = (step) => {
      const j0 = Math.floor(bounds.ymin / step);
      const j1 = Math.ceil(bounds.ymax / step);
      if (!Number.isFinite(j0) || !Number.isFinite(j1) || j1 - j0 > 400) return;
      for (let j = j0; j <= j1; j++) {
        const sy = Math.round(worldToScreenY(j * step)) + 0.5;
        if (sy >= -2 && sy <= height + 2) { ctx.moveTo(0, sy); ctx.lineTo(width, sy); }
      }
    };

    if (settings.showGrid) {
      ctx.strokeStyle = colMinor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      drawVLines(stepX / 4);
      drawHLines(stepY / 4);
      ctx.stroke();

      ctx.strokeStyle = colMajor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      drawVLines(stepX);
      drawHLines(stepY);
      ctx.stroke();
    }

    const ax = worldToScreenX(0);
    const ay = worldToScreenY(0);
    ctx.strokeStyle = colAxis;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    if (Number.isFinite(ax) && ax >= 0 && ax <= width) { ctx.moveTo(ax, 0); ctx.lineTo(ax, height); }
    if (Number.isFinite(ay) && ay >= 0 && ay <= height) { ctx.moveTo(0, ay); ctx.lineTo(width, ay); }
    ctx.stroke();

    if (settings.showAxisLabels) {
      ctx.fillStyle = colLabel;
      ctx.font = '500 11px "Roboto Mono", ui-monospace, monospace';
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const labelY = Number.isFinite(ay) ? Math.min(Math.max(ay + 7, 10), height - 22) : height - 22;

      const ix0 = Math.floor(bounds.xmin / stepX);
      const ix1 = Math.ceil(bounds.xmax / stepX);
      if (Number.isFinite(ix0) && Number.isFinite(ix1) && ix1 - ix0 <= 200) {
        for (let i = ix0; i <= ix1; i++) {
          if (i === 0) continue;
          const x = i * stepX;
          const sx = worldToScreenX(x);
          if (sx > 28 && sx < width - 28) ctx.fillText(formatTick(x, piMode, stepX), sx, labelY);
        }
      }

      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      const labelX = Number.isFinite(ax) ? Math.min(Math.max(ax - 8, 42), width - 10) : 48;

      const iy0 = Math.floor(bounds.ymin / stepY);
      const iy1 = Math.ceil(bounds.ymax / stepY);
      if (Number.isFinite(iy0) && Number.isFinite(iy1) && iy1 - iy0 <= 200) {
        for (let j = iy0; j <= iy1; j++) {
          if (j === 0) continue;
          const y = j * stepY;
          const sy = worldToScreenY(y);
          if (sy > 16 && sy < height - 16) ctx.fillText(formatTick(y, false, stepY), labelX, sy);
        }
      }
    }
  }

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function clipSegment(x0, y0, x1, y1, minX, minY, maxX, maxY) {
    if (!Number.isFinite(x0) || !Number.isFinite(y0) || !Number.isFinite(x1) || !Number.isFinite(y1)) {
      return null;
    }
    const INSIDE = 0, LEFT = 1, RIGHT = 2, BOTTOM = 4, TOP = 8;
    const code = (x, y) => {
      let c = INSIDE;
      if (x < minX) c |= LEFT;
      else if (x > maxX) c |= RIGHT;
      if (y < minY) c |= TOP;
      else if (y > maxY) c |= BOTTOM;
      return c;
    };
    let c0 = code(x0, y0);
    let c1 = code(x1, y1);
    for (let iter = 0; iter < 12; iter++) {
      if ((c0 | c1) === 0) return [x0, y0, x1, y1];
      if ((c0 & c1) !== 0) return null;
      const out = c0 !== 0 ? c0 : c1;
      let x = 0, y = 0;
      if (out & BOTTOM) {
        x = x0 + (x1 - x0) * ((maxY - y0) / (y1 - y0));
        y = maxY;
      } else if (out & TOP) {
        x = x0 + (x1 - x0) * ((minY - y0) / (y1 - y0));
        y = minY;
      } else if (out & RIGHT) {
        y = y0 + (y1 - y0) * ((maxX - x0) / (x1 - x0));
        x = maxX;
      } else {
        y = y0 + (y1 - y0) * ((minX - x0) / (x1 - x0));
        x = minX;
      }
      if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
      if (out === c0) { x0 = x; y0 = y; c0 = code(x0, y0); }
      else { x1 = x; y1 = y; c1 = code(x1, y1); }
    }
    return null;
  }

  function getActiveKeyPoints() {
    if (!settings.showKeyPoints || mode3D) return [];
    const activeEx = expressions.find((e) => e.id === activeExprId && e.visible && e.result?.key_points?.length);
    if (!activeEx) return [];
    const col = getColor(activeEx.colorIdx);
    return activeEx.result.key_points.map((kp) => ({ ...kp, color: col, exprId: activeEx.id }));
  }

  function drawKeyPointBadge(sx, sy, x, y, type) {
    const dark = !isLight();
    const coordStr = `(${formatHudCoord(x)}, ${formatHudCoord(y)})`;
    const tagStr = KP_LABELS[type] || "";
    const text = tagStr ? `${coordStr} · ${tagStr}` : coordStr;

    ctx.save();
    ctx.font = '500 11px "Roboto Mono", ui-monospace, monospace';
    const tw = ctx.measureText(text).width;
    const bw = tw + 16;
    const bh = 24;
    let bx = sx - bw / 2;
    let by = sy - bh - 12;
    if (bx < 12) bx = 12;
    if (bx + bw > width - 12) bx = width - bw - 12;
    if (by < 12) by = sy + 14;

    ctx.fillStyle = dark ? "rgba(24, 24, 27, 0.90)" : "rgba(255, 255, 255, 0.94)";
    ctx.strokeStyle = dark ? "rgba(255, 255, 255, 0.16)" : "rgba(24, 24, 27, 0.16)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(bx, by, bw, bh, 8);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = dark ? "#fafafa" : "#09090b";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, bx + bw / 2, by + bh / 2 + 0.5);
    ctx.restore();
  }

  function strokePolyline(points, col, lw, dash, opacity, isActive, dark) {
    const pad = 40;
    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.strokeStyle = col;
    ctx.lineWidth = lw;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    if (dash && dash.length) ctx.setLineDash(dash);
    if (dark && isActive) {
      ctx.shadowColor = hexToRgba(col, 0.35);
      ctx.shadowBlur = 9;
    }

    ctx.beginPath();
    let prevPt = null;
    let visCount = 0;
    let minSX = Infinity, maxSX = -Infinity, minSY = Infinity, maxSY = -Infinity;
    for (const pt of points) {
      if (pt === null) { prevPt = null; continue; }
      const sx = worldToScreenX(pt[0]);
      const sy = worldToScreenY(pt[1]);
      if (sx >= -10 && sx <= width + 10 && sy >= -10 && sy <= height + 10) {
        visCount++;
        if (sx < minSX) minSX = sx;
        if (sx > maxSX) maxSX = sx;
        if (sy < minSY) minSY = sy;
        if (sy > maxSY) maxSY = sy;
      }
      if (prevPt !== null) {
        const clipped = clipSegment(prevPt[0], prevPt[1], sx, sy, -pad, -pad, width + pad, height + pad);
        if (clipped) {
          ctx.moveTo(clipped[0], clipped[1]);
          ctx.lineTo(clipped[2], clipped[3]);
        }
      }
      prevPt = [sx, sy];
    }
    ctx.stroke();

    if (visCount > 0 && (maxSX - minSX) < 2.5 && (maxSY - minSY) < 2.5) {
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.arc(0.5 * (minSX + maxSX), 0.5 * (minSY + maxSY), Math.max(2.4, lw * 0.9), 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();
    }
    ctx.restore();
  }

  function drawCurves() {
    const dark = !isLight();
    const pad = 40;

    for (const ex of expressions) {
      if (!ex.visible || !ex.result) continue;
      const res = ex.result;
      const col = getColor(ex.colorIdx);
      const st = getExprStyle(ex);

      if (res.kind === "point" && Array.isArray(res.point)) {
        const sx = worldToScreenX(res.point[0]);
        const sy = worldToScreenY(res.point[1]);
        if (Number.isFinite(sx) && Number.isFinite(sy) && sx >= -20 && sx <= width + 20 && sy >= -20 && sy <= height + 20) {
          ctx.save();
          ctx.globalAlpha = st.opacity;
          if (dark) { ctx.shadowColor = hexToRgba(col, 0.5); ctx.shadowBlur = 10; }
          ctx.beginPath();
          ctx.arc(sx, sy, ex.id === activeExprId ? 6.2 : 5.2, 0, Math.PI * 2);
          ctx.fillStyle = col;
          ctx.fill();
          ctx.lineWidth = 2.2;
          ctx.strokeStyle = dark ? "#09090b" : "#ffffff";
          ctx.stroke();
          ctx.restore();
        }
        continue;
      }

      if (res.kind === "table_points" && Array.isArray(res.points)) {
        ctx.save();
        ctx.globalAlpha = st.opacity;
        for (const pt of res.points) {
          const sx = worldToScreenX(pt[0]);
          const sy = worldToScreenY(pt[1]);
          if (sx < -20 || sx > width + 20 || sy < -20 || sy > height + 20) continue;
          ctx.beginPath();
          ctx.arc(sx, sy, 5.0, 0, Math.PI * 2);
          ctx.fillStyle = col;
          ctx.fill();
          ctx.lineWidth = 2;
          ctx.strokeStyle = dark ? "#09090b" : "#ffffff";
          ctx.stroke();
        }
        ctx.restore();
        continue;
      }

      if (res.kind === "integral_area" && res.points?.length) {
        const y0Screen = Math.max(-pad, Math.min(height + pad, worldToScreenY(0)));
        const clampX = (v) => Math.max(-pad, Math.min(width + pad, v));
        const clampY = (v) => Math.max(-pad, Math.min(height + pad, v));

        ctx.save();
        ctx.fillStyle = hexToRgba(col, (dark ? 0.24 : 0.22) * st.opacity);
        let seg = [];
        const flushArea = () => {
          if (seg.length < 2) { seg = []; return; }
          ctx.beginPath();
          ctx.moveTo(clampX(worldToScreenX(seg[0][0])), y0Screen);
          for (const pt of seg) {
            ctx.lineTo(clampX(worldToScreenX(pt[0])), clampY(worldToScreenY(pt[1])));
          }
          ctx.lineTo(clampX(worldToScreenX(seg[seg.length - 1][0])), y0Screen);
          ctx.closePath();
          ctx.fill();
          seg = [];
        };
        for (const pt of res.points) {
          if (pt === null) flushArea();
          else seg.push(pt);
        }
        flushArea();
        ctx.restore();

        if (Array.isArray(res.bounds) && res.bounds.length === 2) {
          ctx.save();
          ctx.strokeStyle = hexToRgba(col, 0.55 * st.opacity);
          ctx.lineWidth = 1.3;
          ctx.setLineDash([4, 4]);
          for (const bx of res.bounds) {
            const sx = worldToScreenX(bx);
            if (sx >= -10 && sx <= width + 10) {
              ctx.beginPath();
              ctx.moveTo(sx, y0Screen);
              const match = res.points.find((p) => p && Math.abs(p[0] - bx) < 1e-3);
              const ty = match ? clampY(worldToScreenY(match[1])) : y0Screen;
              ctx.lineTo(sx, ty);
              ctx.stroke();
            }
          }
          ctx.restore();
        }

        strokePolyline(res.points, col, st.width, st.dash, st.opacity, ex.id === activeExprId, dark);
        continue;
      }

      if (res.kind === "curve_family" && Array.isArray(res.curves)) {
        const total = res.curves.length;
        res.curves.forEach((pts, idx) => {
          const fade = total > 1 ? 0.42 + 0.58 * (idx / (total - 1)) : 1.0;
          strokePolyline(pts, col, Math.max(1.6, st.width * 0.85), st.dash, st.opacity * fade, false, dark);
        });
        continue;
      }

      if (res.kind === "slope_field" && Array.isArray(res.arrows)) {
        const segLen = Math.min(26, Math.max(12, Math.min(width / 26, height / 20) * 0.62));
        const half = segLen * 0.5;
        ctx.save();
        ctx.globalAlpha = 0.78 * st.opacity;
        ctx.strokeStyle = col;
        ctx.lineWidth = Math.max(1.2, st.width * 0.65);
        ctx.lineCap = "round";
        ctx.beginPath();
        for (const a of res.arrows) {
          const sx = worldToScreenX(a[0]);
          const sy = worldToScreenY(a[1]);
          const m = a[2];
          if (!Number.isFinite(sx) || !Number.isFinite(sy) || !Number.isFinite(m)) continue;
          const norm = Math.hypot(1, m);
          const ux = 1 / norm;
          const uy = -m / norm;
          const x0 = sx - ux * half;
          const y0 = sy - uy * half;
          const x1 = sx + ux * half;
          const y1 = sy + uy * half;
          ctx.moveTo(x0, y0);
          ctx.lineTo(x1, y1);
          const head = 4.2;
          const ax1 = x1 - head * (ux * 0.85 - uy * 0.52);
          const ay1 = y1 - head * (uy * 0.85 + ux * 0.52);
          const ax2 = x1 - head * (ux * 0.85 + uy * 0.52);
          const ay2 = y1 - head * (uy * 0.85 - ux * 0.52);
          ctx.moveTo(ax1, ay1);
          ctx.lineTo(x1, y1);
          ctx.lineTo(ax2, ay2);
        }
        ctx.stroke();
        ctx.restore();
        continue;
      }

      if ((res.kind === "curve" || res.kind === "regression") && res.points && res.points.length) {
        if (res.inequality) {
          ctx.save();
          ctx.fillStyle = hexToRgba(col, (dark ? 0.14 : 0.13) * st.opacity);
          const edgeY = res.inequality === "above" ? -10 : height + 10;
          const clampX = (v) => Math.max(-pad, Math.min(width + pad, v));
          const clampY = (v) => Math.max(-pad, Math.min(height + pad, v));
          let seg = [];
          const flushPoly = () => {
            if (seg.length < 2) { seg = []; return; }
            ctx.beginPath();
            ctx.moveTo(clampX(worldToScreenX(seg[0][0])), edgeY);
            for (const pt of seg) {
              ctx.lineTo(clampX(worldToScreenX(pt[0])), clampY(worldToScreenY(pt[1])));
            }
            ctx.lineTo(clampX(worldToScreenX(seg[seg.length - 1][0])), edgeY);
            ctx.closePath();
            ctx.fill();
            seg = [];
          };
          for (const pt of res.points) {
            if (pt === null) flushPoly();
            else seg.push(pt);
          }
          flushPoly();
          ctx.restore();
        }

        const effDash = res.strict && st.dash.length === 0 ? [6, 6] : st.dash;
        strokePolyline(res.points, col, st.width, effDash, st.opacity, ex.id === activeExprId, dark);

        if (ex.showTable && Array.isArray(res.table)) {
          ctx.save();
          ctx.globalAlpha = st.opacity;
          for (const row of res.table) {
            if (row[1] === null || !Number.isFinite(row[0]) || !Number.isFinite(row[1])) continue;
            const sx = worldToScreenX(row[0]);
            const sy = worldToScreenY(row[1]);
            if (sx < -15 || sx > width + 15 || sy < -15 || sy > height + 15) continue;
            ctx.beginPath();
            ctx.arc(sx, sy, 4.3, 0, Math.PI * 2);
            ctx.fillStyle = dark ? "#09090b" : "#ffffff";
            ctx.fill();
            ctx.lineWidth = 2.2;
            ctx.strokeStyle = col;
            ctx.stroke();
          }
          ctx.restore();
        }
      }

      if (res.kind === "rect_region") {
        const x0 = res.x_lo !== null ? worldToScreenX(res.x_lo) : -pad;
        const x1 = res.x_hi !== null ? worldToScreenX(res.x_hi) : width + pad;
        const yTop = res.y_hi !== null ? worldToScreenY(res.y_hi) : -pad;
        const yBot = res.y_lo !== null ? worldToScreenY(res.y_lo) : height + pad;
        const rx = Math.max(-pad, Math.min(width + pad, Math.min(x0, x1)));
        const ry = Math.max(-pad, Math.min(height + pad, Math.min(yTop, yBot)));
        const rx2 = Math.max(-pad, Math.min(width + pad, Math.max(x0, x1)));
        const ry2 = Math.max(-pad, Math.min(height + pad, Math.max(yTop, yBot)));
        const rw = rx2 - rx;
        const rh = ry2 - ry;
        if (rw >= 0 && rh >= 0 && rx2 >= 0 && rx <= width && ry2 >= 0 && ry <= height) {
          ctx.save();
          ctx.fillStyle = hexToRgba(col, (dark ? 0.22 : 0.18) * st.opacity);
          ctx.fillRect(rx, ry, Math.max(rw, 1.5), Math.max(rh, 1.5));

          ctx.strokeStyle = col;
          ctx.globalAlpha = st.opacity;
          ctx.lineWidth = Math.max(1.6, st.width * 0.85);
          const drawEdge = (ax0, ay0, ax1, ay1, isStrict) => {
            ctx.beginPath();
            ctx.setLineDash(isStrict ? [6, 5] : st.dash);
            ctx.moveTo(ax0, ay0);
            ctx.lineTo(ax1, ay1);
            ctx.stroke();
          };
          if (res.x_lo !== null) drawEdge(x0, ry, x0, ry2, Boolean(res.strict_x?.[0]));
          if (res.x_hi !== null) drawEdge(x1, ry, x1, ry2, Boolean(res.strict_x?.[1]));
          if (res.y_lo !== null) drawEdge(rx, yBot, rx2, yBot, Boolean(res.strict_y?.[0]));
          if (res.y_hi !== null) drawEdge(rx, yTop, rx2, yTop, Boolean(res.strict_y?.[1]));
          ctx.restore();
        }
        continue;
      }

      if (res.kind === "implicit") {
        if (res.shade) {
          const { w, h, bits, bounds: sb } = res.shade;
          const off = document.createElement("canvas");
          off.width = w; off.height = h;
          const octx = off.getContext("2d");
          const img = octx.createImageData(w, h);
          const r = parseInt(col.slice(1, 3), 16);
          const g = parseInt(col.slice(3, 5), 16);
          const b = parseInt(col.slice(5, 7), 16);
          const a = Math.round((dark ? 38 : 34) * st.opacity);
          for (let i = 0; i < bits.length; i++) {
            if (bits[i] === "1") {
              const p = i * 4;
              img.data[p] = r; img.data[p + 1] = g; img.data[p + 2] = b; img.data[p + 3] = a;
            }
          }
          octx.putImageData(img, 0, 0);
          ctx.save();
          ctx.imageSmoothingEnabled = true;
          if (sb && sb.length === 4) {
            const xL = worldToScreenX(sb[0]);
            const xR = worldToScreenX(sb[1]);
            const yT = worldToScreenY(sb[3]);
            const yB = worldToScreenY(sb[2]);
            if (Number.isFinite(xL) && Number.isFinite(xR) && Number.isFinite(yT) && Number.isFinite(yB)) {
              ctx.drawImage(off, xL, yT, xR - xL, yB - yT);
            }
          } else {
            ctx.drawImage(off, 0, 0, width, height);
          }
          ctx.restore();
        }

        if (res.segments && res.segments.length) {
          ctx.save();
          ctx.globalAlpha = st.opacity;
          ctx.strokeStyle = col;
          ctx.lineWidth = st.width;
          ctx.lineCap = "round";
          const effDash = res.strict && st.dash.length === 0 ? [6, 6] : st.dash;
          if (effDash.length) ctx.setLineDash(effDash);
          if (dark && ex.id === activeExprId) {
            ctx.shadowColor = hexToRgba(col, 0.35);
            ctx.shadowBlur = 8;
          }

          ctx.beginPath();
          let visCount = 0;
          let minSX = Infinity, maxSX = -Infinity, minSY = Infinity, maxSY = -Infinity;
          for (const s of res.segments) {
            const sx0 = worldToScreenX(s[0]);
            const sy0 = worldToScreenY(s[1]);
            const sx1 = worldToScreenX(s[2]);
            const sy1 = worldToScreenY(s[3]);
            const clipped = clipSegment(sx0, sy0, sx1, sy1, -pad, -pad, width + pad, height + pad);
            if (clipped) {
              ctx.moveTo(clipped[0], clipped[1]);
              ctx.lineTo(clipped[2], clipped[3]);
              visCount++;
              minSX = Math.min(minSX, clipped[0], clipped[2]);
              maxSX = Math.max(maxSX, clipped[0], clipped[2]);
              minSY = Math.min(minSY, clipped[1], clipped[3]);
              maxSY = Math.max(maxSY, clipped[1], clipped[3]);
            }
          }
          ctx.stroke();

          if (visCount > 0 && (maxSX - minSX) < 2.5 && (maxSY - minSY) < 2.5) {
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.arc(0.5 * (minSX + maxSX), 0.5 * (minSY + maxSY), Math.max(2.4, st.width * 0.9), 0, Math.PI * 2);
            ctx.fillStyle = col;
            ctx.fill();
          }
          ctx.restore();
        }
      }
    }

    const activeKps = getActiveKeyPoints();
    for (const kp of activeKps) {
      const sx = worldToScreenX(kp.x);
      const sy = worldToScreenY(kp.y);
      if (!Number.isFinite(sx) || !Number.isFinite(sy) || sx < -12 || sx > width + 12 || sy < -12 || sy > height + 12) continue;
      const isHov = hoveredKeyPoint && Math.hypot(worldToScreenX(hoveredKeyPoint.x) - sx, worldToScreenY(hoveredKeyPoint.y) - sy) < 4;
      const isPin = pinnedKeyPoints.some((p) => Math.abs(p.x - kp.x) < 1e-5 && Math.abs(p.y - kp.y) < 1e-5);
      ctx.save();
      ctx.beginPath();
      ctx.arc(sx, sy, isHov || isPin ? 5.2 : 4.2, 0, Math.PI * 2);
      ctx.fillStyle = isHov || isPin ? (dark ? "#fafafa" : "#18181b") : (dark ? "#a1a1aa" : "#71717a");
      ctx.fill();
      ctx.lineWidth = 1.8;
      ctx.strokeStyle = dark ? "#09090b" : "#ffffff";
      ctx.stroke();
      ctx.restore();
    }

    for (const pk of pinnedKeyPoints) {
      const sx = worldToScreenX(pk.x);
      const sy = worldToScreenY(pk.y);
      if (Number.isFinite(sx) && Number.isFinite(sy) && sx >= -20 && sx <= width + 20 && sy >= -20 && sy <= height + 20) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(sx, sy, 5.2, 0, Math.PI * 2);
        ctx.fillStyle = dark ? "#fafafa" : "#18181b";
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = dark ? "#09090b" : "#ffffff";
        ctx.stroke();
        ctx.restore();
        drawKeyPointBadge(sx, sy, pk.x, pk.y, pk.type);
      }
    }

    if (tracePoint) {
      const sx = worldToScreenX(tracePoint.x);
      const sy = worldToScreenY(tracePoint.y);

      if (settings.showTangent && Number.isFinite(tracePoint.slope)) {
        const m = tracePoint.slope;
        const len = Math.hypot(width, height);
        const norm = Math.hypot(1, m);
        const ux = 1 / norm;
        const uy = -m / norm;
        const clipped = clipSegment(
          sx - ux * len, sy - uy * len,
          sx + ux * len, sy + uy * len,
          -pad, -pad, width + pad, height + pad
        );
        if (clipped) {
          ctx.save();
          ctx.strokeStyle = hexToRgba(tracePoint.color, dark ? 0.55 : 0.50);
          ctx.lineWidth = 1.5;
          ctx.setLineDash([6, 5]);
          ctx.beginPath();
          ctx.moveTo(clipped[0], clipped[1]);
          ctx.lineTo(clipped[2], clipped[3]);
          ctx.stroke();
          ctx.restore();
        }
      }

      if (Number.isFinite(sx) && Number.isFinite(sy)) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(sx, sy, 5.5, 0, Math.PI * 2);
        ctx.fillStyle = tracePoint.color;
        ctx.fill();
        ctx.lineWidth = 2.2;
        ctx.strokeStyle = isLight() ? "#ffffff" : "#09090b";
        ctx.stroke();
        ctx.restore();
      }
    }
  }

  function project3D(nx, ny, nz) {
    const cy = Math.cos(cam3D.yaw);
    const sy = Math.sin(cam3D.yaw);
    const cp = Math.cos(cam3D.pitch);
    const sp = Math.sin(cam3D.pitch);

    const x1 = nx * cy - ny * sy;
    const y1 = nx * sy + ny * cy;
    const z1 = nz;

    const y2 = y1 * cp - z1 * sp;
    const z2 = y1 * sp + z1 * cp;

    const fov = 3.4;
    const depth = fov + y2;
    const scale = (Math.min(width, height) * 0.42 * cam3D.zoom) / Math.max(depth, 0.4);
    const centerOffsetX = sidebar.classList.contains("collapsed") ? 0 : 180;
    const cx = width / 2 + centerOffsetX * 0.45;
    const cyScr = height / 2 + 12;
    return { sx: cx + x1 * scale, sy: cyScr - z2 * scale, depth };
  }

  function drawScene3D() {
    const dark = !isLight();
    const cs = getComputedStyle(document.documentElement);
    const colMajor = cs.getPropertyValue("--grid-major").trim();
    const colAxis = cs.getPropertyValue("--grid-axis").trim();
    const colLabel = cs.getPropertyValue("--grid-label").trim();

    if (settings.showGrid) {
      ctx.save();
      ctx.strokeStyle = colMajor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let i = -4; i <= 4; i++) {
        const t = i / 4;
        const a = project3D(t, -1, 0);
        const b = project3D(t, 1, 0);
        ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy);
        const c = project3D(-1, t, 0);
        const d = project3D(1, t, 0);
        ctx.moveTo(c.sx, c.sy); ctx.lineTo(d.sx, d.sy);
      }
      ctx.stroke();
      ctx.restore();
    }

    ctx.save();
    ctx.strokeStyle = colAxis;
    ctx.lineWidth = 1.5;
    const axes = [
      { from: [-1.15, 0, 0], to: [1.15, 0, 0], label: "x" },
      { from: [0, -1.15, 0], to: [0, 1.15, 0], label: "y" },
      { from: [0, 0, -0.9], to: [0, 0, 1.05], label: "z" },
    ];
    ctx.font = '600 12px "Roboto Mono", ui-monospace, monospace';
    ctx.fillStyle = colLabel;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (const ax of axes) {
      const p0 = project3D(...ax.from);
      const p1 = project3D(...ax.to);
      ctx.beginPath();
      ctx.moveTo(p0.sx, p0.sy);
      ctx.lineTo(p1.sx, p1.sy);
      ctx.stroke();
      const lp = project3D(ax.to[0] * 1.08, ax.to[1] * 1.08, ax.to[2] * 1.08);
      ctx.fillText(ax.label, lp.sx, lp.sy);
    }
    ctx.restore();

    const quads = [];
    const curves3D = [];
    const points3D = [];
    let has3DObject = false;

    const worldRadius = Math.max(2.5, Math.min(0.5 * Math.min(width, height) / Math.max(view.scale, 1e-6), 1e120));
    let globalMaxAbs = 1.0;
    for (const ex of expressions) {
      if (!ex.visible || !ex.result) continue;
      const r = ex.result;
      if (r.kind === "implicit3d" && Array.isArray(r.verts)) {
        for (const v of r.verts) globalMaxAbs = Math.max(globalMaxAbs, Math.abs(v[0]), Math.abs(v[1]), Math.abs(v[2]));
      } else if (r.kind === "parametric_surface3d" && Array.isArray(r.Z)) {
        const nv = r.Z.length, nu = nv > 0 ? r.Z[0].length : 0;
        for (let i = 0; i < nv; i++) {
          for (let j = 0; j < nu; j++) {
            const xv = r.X[i][j], yv = r.Y[i][j], zv = r.Z[i][j];
            if (xv !== null && yv !== null && zv !== null) {
              globalMaxAbs = Math.max(globalMaxAbs, Math.abs(xv), Math.abs(yv), Math.abs(zv));
            }
          }
        }
      } else if (r.kind === "curve3d" && Array.isArray(r.points)) {
        for (const pt of r.points) {
          if (pt) globalMaxAbs = Math.max(globalMaxAbs, Math.abs(pt[0]), Math.abs(pt[1]), Math.abs(pt[2]));
        }
      } else if (r.kind === "point3d" && Array.isArray(r.point)) {
        globalMaxAbs = Math.max(globalMaxAbs, Math.abs(r.point[0]), Math.abs(r.point[1]), Math.abs(r.point[2]));
      }
    }
    const globalNormDiv = Math.max(globalMaxAbs, 1.0);

    for (const ex of expressions) {
      if (!ex.visible || !ex.result) continue;
      const res = ex.result;
      const col = getColor(ex.colorIdx);
      const st = getExprStyle(ex);

      if (res.kind === "parametric_surface3d") {
        has3DObject = true;
        const { X, Y, Z, zmin, zmax } = res;
        const nv = Z.length;
        const nu = nv > 0 ? Z[0].length : 0;
        if (nu < 2 || nv < 2) continue;

        let maxAbs = 1e-6;
        for (let r = 0; r < nv; r++) {
          for (let c = 0; c < nu; c++) {
            const xv = X[r][c], yv = Y[r][c], zv = Z[r][c];
            if (xv !== null && yv !== null && zv !== null) {
              maxAbs = Math.max(maxAbs, Math.abs(xv), Math.abs(yv), Math.abs(zv));
            }
          }
        }
        const normDiv = globalNormDiv;
        const zSpan = Math.max(zmax - zmin, 1e-9);

        const projGrid = Array.from({ length: nv }, () => new Array(nu));
        for (let r = 0; r < nv; r++) {
          for (let c = 0; c < nu; c++) {
            const xv = X[r][c], yv = Y[r][c], zv = Z[r][c];
            if (xv === null || yv === null || zv === null) {
              projGrid[r][c] = null;
              continue;
            }
            projGrid[r][c] = {
              ...project3D(xv / normDiv, yv / normDiv, zv / normDiv),
              t: Math.max(0, Math.min(1, (zv - zmin) / zSpan)),
            };
          }
        }

        const rBase = parseInt(col.slice(1, 3), 16);
        const gBase = parseInt(col.slice(3, 5), 16);
        const bBase = parseInt(col.slice(5, 7), 16);

        for (let r = 0; r < nv - 1; r++) {
          for (let c = 0; c < nu - 1; c++) {
            const p00 = projGrid[r][c];
            const p10 = projGrid[r][c + 1];
            const p11 = projGrid[r + 1][c + 1];
            const p01 = projGrid[r + 1][c];
            if (!p00 || !p10 || !p11 || !p01) continue;
            const avgDepth = 0.25 * (p00.depth + p10.depth + p11.depth + p01.depth);
            const hNorm = 0.25 * (p00.t + p10.t + p11.t + p01.t);
            const shade = dark ? (0.34 + 0.66 * hNorm) : (0.55 + 0.45 * hNorm);
            const fill = `rgba(${Math.round(rBase * shade)}, ${Math.round(gBase * shade)}, ${Math.round(bBase * shade)}, ${(0.76 * st.opacity).toFixed(3)})`;
            const stroke = dark
              ? `rgba(9, 9, 11, ${(0.42 * st.opacity).toFixed(3)})`
              : `rgba(255, 255, 255, ${(0.42 * st.opacity).toFixed(3)})`;
            quads.push({ p00, p10, p11, p01, depth: avgDepth, fill, stroke });
          }
        }
        continue;
      }

      if (res.kind === "curve3d" && Array.isArray(res.points)) {
        has3DObject = true;
        let maxAbs = worldRadius;
        for (const pt of res.points) {
          if (pt) maxAbs = Math.max(maxAbs, Math.abs(pt[0]), Math.abs(pt[1]), Math.abs(pt[2]));
        }
        const normDiv = globalNormDiv;
        const projPts = res.points.map((pt) => (pt ? project3D(pt[0] / normDiv, pt[1] / normDiv, pt[2] / normDiv) : null));
        curves3D.push({ pts: projPts, col, st });
        continue;
      }

      if (res.kind === "point3d" && Array.isArray(res.point)) {
        has3DObject = true;
        const [px, py, pz] = res.point;
        const normDiv = globalNormDiv;
        points3D.push({ p: project3D(px / normDiv, py / normDiv, pz / normDiv), col, st });
        continue;
      }

      if (res.kind === "implicit3d" && Array.isArray(res.verts) && Array.isArray(res.quads)) {
        has3DObject = true;
        const { verts, quads: qList, zmin, zmax } = res;
        if (verts.length === 0 || qList.length === 0) continue;

        let maxAbs = 1e-6;
        for (const v of verts) {
          maxAbs = Math.max(maxAbs, Math.abs(v[0]), Math.abs(v[1]), Math.abs(v[2]));
        }
        const normDiv = globalNormDiv;
        const zSpan = Math.max(zmax - zmin, 1e-9);

        const projVerts = verts.map((v) => ({
          ...project3D(v[0] / normDiv, v[1] / normDiv, v[2] / normDiv),
          t: Math.max(0, Math.min(1, (v[2] - zmin) / zSpan)),
        }));

        const rBase = parseInt(col.slice(1, 3), 16);
        const gBase = parseInt(col.slice(3, 5), 16);
        const bBase = parseInt(col.slice(5, 7), 16);

        const isFlat = Boolean(res.is_flat);
        const zPlane = Number(res.z_plane) || 0;
        const camSignZ = Math.sin(cam3D.pitch) >= 0 ? 1 : -1;
        let depthBias = 0;
        if (isFlat) {
          const onFrontSide = (zPlane * camSignZ) >= 0;
          depthBias = onFrontSide
            ? (-0.045 - 0.08 * (Math.abs(zPlane) / normDiv))
            : (0.045 + 0.08 * (Math.abs(zPlane) / normDiv));
        }

        for (const q of qList) {
          const p00 = projVerts[q[0]];
          const p10 = projVerts[q[1]];
          const p11 = projVerts[q[2]];
          const p01 = projVerts[q[3]];
          if (!p00 || !p10 || !p11 || !p01) continue;
          const avgDepth = 0.25 * (p00.depth + p10.depth + p11.depth + p01.depth) + depthBias;
          const hNorm = 0.25 * (p00.t + p10.t + p11.t + p01.t);
          const shade = isFlat ? (dark ? 0.88 : 0.92) : (dark ? (0.34 + 0.66 * hNorm) : (0.55 + 0.45 * hNorm));
          const alpha = isFlat ? (0.94 * st.opacity) : (0.78 * st.opacity);
          const fill = `rgba(${Math.round(rBase * shade)}, ${Math.round(gBase * shade)}, ${Math.round(bBase * shade)}, ${alpha.toFixed(3)})`;
          const stroke = isFlat
            ? fill
            : (dark
                ? `rgba(9, 9, 11, ${(0.38 * st.opacity).toFixed(3)})`
                : `rgba(255, 255, 255, ${(0.38 * st.opacity).toFixed(3)})`);
          quads.push({ p00, p10, p11, p01, depth: avgDepth, fill, stroke });
        }
        continue;
      }

      if (res.kind !== "surface3d") continue;
      has3DObject = true;
      const { gx, gy, gz, zmin, zmax } = res;
      const ny = gy.length;
      const nx = gx.length;
      if (nx < 2 || ny < 2) continue;

      const xMid = 0.5 * (gx[0] + gx[nx - 1]);
      const yMid = 0.5 * (gy[0] + gy[ny - 1]);
      const xHalf = Math.max(0.5 * (gx[nx - 1] - gx[0]), 1e-9);
      const yHalf = Math.max(0.5 * (gy[ny - 1] - gy[0]), 1e-9);
      const zMid = 0.5 * (zmin + zmax);
      const zHalf = Math.max(0.5 * (zmax - zmin), 1e-9);

      const projGrid = Array.from({ length: ny }, () => new Array(nx));
      for (let r = 0; r < ny; r++) {
        const nyNorm = (gy[r] - yMid) / yHalf;
        for (let c = 0; c < nx; c++) {
          const zv = gz[r][c];
          if (zv === null || !Number.isFinite(zv)) {
            projGrid[r][c] = null;
            continue;
          }
          const nxNorm = (gx[c] - xMid) / xHalf;
          const nzNorm = Math.max(-1.2, Math.min(1.2, ((zv - zMid) / zHalf) * 0.72));
          projGrid[r][c] = { ...project3D(nxNorm, nyNorm, nzNorm), t: Math.max(0, Math.min(1, (zv - zmin) / (zmax - zmin))) };
        }
      }

      const rBase = parseInt(col.slice(1, 3), 16);
      const gBase = parseInt(col.slice(3, 5), 16);
      const bBase = parseInt(col.slice(5, 7), 16);

      for (let r = 0; r < ny - 1; r++) {
        for (let c = 0; c < nx - 1; c++) {
          const p00 = projGrid[r][c];
          const p10 = projGrid[r][c + 1];
          const p11 = projGrid[r + 1][c + 1];
          const p01 = projGrid[r + 1][c];
          if (!p00 || !p10 || !p11 || !p01) continue;
          const avgDepth = 0.25 * (p00.depth + p10.depth + p11.depth + p01.depth);
          const hNorm = 0.25 * (p00.t + p10.t + p11.t + p01.t);
          const shade = dark ? (0.34 + 0.66 * hNorm) : (0.55 + 0.45 * hNorm);
          const fill = `rgba(${Math.round(rBase * shade)}, ${Math.round(gBase * shade)}, ${Math.round(bBase * shade)}, ${(0.72 * st.opacity).toFixed(3)})`;
          const stroke = dark
            ? `rgba(9, 9, 11, ${(0.45 * st.opacity).toFixed(3)})`
            : `rgba(255, 255, 255, ${(0.45 * st.opacity).toFixed(3)})`;
          quads.push({ p00, p10, p11, p01, depth: avgDepth, fill, stroke });
        }
      }
    }

    quads.sort((a, b) => b.depth - a.depth);
    ctx.save();
    ctx.lineWidth = 0.7;
    for (const q of quads) {
      ctx.beginPath();
      ctx.moveTo(q.p00.sx, q.p00.sy);
      ctx.lineTo(q.p10.sx, q.p10.sy);
      ctx.lineTo(q.p11.sx, q.p11.sy);
      ctx.lineTo(q.p01.sx, q.p01.sy);
      ctx.closePath();
      ctx.fillStyle = q.fill;
      ctx.fill();
      ctx.strokeStyle = q.stroke;
      ctx.stroke();
    }
    ctx.restore();

    for (const c3 of curves3D) {
      ctx.save();
      ctx.globalAlpha = c3.st.opacity;
      ctx.strokeStyle = c3.col;
      ctx.lineWidth = c3.st.width;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      if (c3.st.dash?.length) ctx.setLineDash(c3.st.dash);
      ctx.beginPath();
      let started = false;
      for (const p of c3.pts) {
        if (!p) { started = false; continue; }
        if (!started) { ctx.moveTo(p.sx, p.sy); started = true; }
        else ctx.lineTo(p.sx, p.sy);
      }
      ctx.stroke();
      ctx.restore();
    }

    for (const pt3 of points3D) {
      ctx.save();
      ctx.globalAlpha = pt3.st.opacity;
      ctx.beginPath();
      ctx.arc(pt3.p.sx, pt3.p.sy, 5.5, 0, Math.PI * 2);
      ctx.fillStyle = pt3.col;
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = dark ? "#09090b" : "#ffffff";
      ctx.stroke();
      ctx.restore();
    }
  }

  function drawScene() {
    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    if (mode3D) {
      drawScene3D();
    } else {
      drawGrid();
      drawCurves();
    }
    ctx.restore();
  }

  function buildPngDataUrl() {
    const exportCanvas = document.createElement("canvas");
    exportCanvas.width = canvas.width;
    exportCanvas.height = canvas.height;
    const ectx = exportCanvas.getContext("2d");
    ectx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--background").trim();
    ectx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
    ectx.drawImage(canvas, 0, 0);
    return exportCanvas.toDataURL("image/png");
  }

  function escapeXml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function buildSvgString() {
    const cs = getComputedStyle(document.documentElement);
    const bg = cs.getPropertyValue("--background").trim();
    const colMinor = cs.getPropertyValue("--grid-minor").trim();
    const colMajor = cs.getPropertyValue("--grid-major").trim();
    const colAxis = cs.getPropertyValue("--grid-axis").trim();
    const colLabel = cs.getPropertyValue("--grid-label").trim();
    const dark = !isLight();
    const pad = 40;
    const f = (n) => Number(n.toFixed(2));

    const out = [
      `<?xml version="1.0" encoding="UTF-8"?>`,
      `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
      `  <rect width="100%" height="100%" fill="${escapeXml(bg)}" />`,
    ];

    if (mode3D) {
      out.push(`  <image href="${buildPngDataUrl()}" width="${width}" height="${height}" />`);
      out.push("</svg>");
      return out.join("\n");
    }

    const bounds = getBounds();
    const { stepX, stepY } = getGridSteps();

    if (settings.showGrid && !settings.polarGrid && Number.isFinite(stepX) && stepX > 0 && Number.isFinite(stepY) && stepY > 0) {
      const buildGridPath = (sxStep, syStep) => {
        const d = [];
        const i0 = Math.floor(bounds.xmin / sxStep);
        const i1 = Math.ceil(bounds.xmax / sxStep);
        if (Number.isFinite(i0) && Number.isFinite(i1) && i1 - i0 <= 400) {
          for (let i = i0; i <= i1; i++) {
            const sx = f(worldToScreenX(i * sxStep));
            if (sx >= -2 && sx <= width + 2) d.push(`M${sx} 0V${height}`);
          }
        }
        const j0 = Math.floor(bounds.ymin / syStep);
        const j1 = Math.ceil(bounds.ymax / syStep);
        if (Number.isFinite(j0) && Number.isFinite(j1) && j1 - j0 <= 400) {
          for (let j = j0; j <= j1; j++) {
            const sy = f(worldToScreenY(j * syStep));
            if (sy >= -2 && sy <= height + 2) d.push(`M0 ${sy}H${width}`);
          }
        }
        return d.join("");
      };
      const dMinor = buildGridPath(stepX / 4, stepY / 4);
      if (dMinor) out.push(`  <path d="${dMinor}" stroke="${escapeXml(colMinor)}" stroke-width="1" fill="none" />`);
      const dMajor = buildGridPath(stepX, stepY);
      if (dMajor) out.push(`  <path d="${dMajor}" stroke="${escapeXml(colMajor)}" stroke-width="1" fill="none" />`);
    }

    const ax = worldToScreenX(0);
    const ay = worldToScreenY(0);
    const axisD = [];
    if (Number.isFinite(ax) && ax >= 0 && ax <= width) axisD.push(`M${f(ax)} 0V${height}`);
    if (Number.isFinite(ay) && ay >= 0 && ay <= height) axisD.push(`M0 ${f(ay)}H${width}`);
    if (axisD.length) {
      out.push(`  <path d="${axisD.join("")}" stroke="${escapeXml(colAxis)}" stroke-width="1.4" fill="none" />`);
    }

    if (settings.polarGrid && Number.isFinite(ax) && Number.isFinite(ay)) {
      const rStep = niceStep(92 / view.scale);
      if (Number.isFinite(rStep) && rStep > 0) {
        const corners = [[0, 0], [width, 0], [0, height], [width, height]];
        let maxPixR = 0, minPixR = Infinity;
        for (const [cx, cy] of corners) {
          const d = Math.hypot(cx - ax, cy - ay);
          if (d > maxPixR) maxPixR = d;
          if (d < minPixR) minPixR = d;
        }
        if (ax >= 0 && ax <= width && ay >= 0 && ay <= height) minPixR = 0;
        const kStart = Math.max(1, Math.floor(Math.max(0, minPixR / view.scale) / rStep));
        const kEnd = Math.min(kStart + 80, Math.ceil((maxPixR / view.scale) / rStep));

        if (settings.showGrid) {
          for (let k = kStart; k <= kEnd; k++) {
            const prMin = (k - 0.5) * rStep * view.scale;
            if (prMin > 4 && prMin < 1e6) {
              out.push(`  <circle cx="${f(ax)}" cy="${f(ay)}" r="${f(prMin)}" stroke="${escapeXml(colMinor)}" stroke-width="1" fill="none" />`);
            }
            const prMaj = k * rStep * view.scale;
            if (prMaj > 4 && prMaj < 1e6) {
              out.push(`  <circle cx="${f(ax)}" cy="${f(ay)}" r="${f(prMaj)}" stroke="${escapeXml(colMajor)}" stroke-width="1" fill="none" />`);
            }
          }
          const rayLen = Math.min(maxPixR + 40, 20000);
          const rayD = [];
          for (let a = 0; a < 12; a++) {
            const ang = (a * Math.PI) / 6;
            const cl = clipSegment(ax, ay, ax + Math.cos(ang) * rayLen, ay - Math.sin(ang) * rayLen, -pad, -pad, width + pad, height + pad);
            if (cl) rayD.push(`M${f(cl[0])} ${f(cl[1])}L${f(cl[2])} ${f(cl[3])}`);
          }
          if (rayD.length) out.push(`  <path d="${rayD.join("")}" stroke="${escapeXml(colMajor)}" stroke-width="1" fill="none" />`);
        }

        if (settings.showAxisLabels) {
          const labelY = Math.min(Math.max(ay + 18, 18), height - 10);
          for (let k = kStart; k <= kEnd; k++) {
            const rVal = k * rStep;
            const sx = ax + rVal * view.scale;
            if (sx > 28 && sx < width - 28) {
              out.push(`  <text x="${f(sx)}" y="${f(labelY)}" fill="${escapeXml(colLabel)}" font-family="Roboto Mono, monospace" font-size="11" text-anchor="middle">${escapeXml(formatTick(rVal, false, rStep))}</text>`);
            }
          }
          const ringR = Math.min(Math.max(120, Math.min(width, height) * 0.36), maxPixR * 0.85);
          const angleLabels = ["0", "π/6", "π/3", "π/2", "2π/3", "5π/6", "π", "7π/6", "4π/3", "3π/2", "5π/3", "11π/6"];
          for (let a = 1; a < 12; a++) {
            if (a === 6) continue;
            const ang = (a * Math.PI) / 6;
            const lx = ax + Math.cos(ang) * ringR;
            const ly = ay - Math.sin(ang) * ringR;
            if (lx > 24 && lx < width - 24 && ly > 18 && ly < height - 18) {
              out.push(`  <text x="${f(lx)}" y="${f(ly + 4)}" fill="${escapeXml(colLabel)}" font-family="Roboto Mono, monospace" font-size="11" text-anchor="middle">${escapeXml(angleLabels[a])}</text>`);
            }
          }
        }
      }
    }

    if (settings.showAxisLabels && !settings.polarGrid && Number.isFinite(stepX) && stepX > 0 && Number.isFinite(stepY) && stepY > 0) {
      const labelY = Number.isFinite(ay) ? Math.min(Math.max(ay + 18, 18), height - 10) : height - 10;
      const ix0 = Math.floor(bounds.xmin / stepX);
      const ix1 = Math.ceil(bounds.xmax / stepX);
      if (Number.isFinite(ix0) && Number.isFinite(ix1) && ix1 - ix0 <= 200) {
        for (let i = ix0; i <= ix1; i++) {
          if (i === 0) continue;
          const sx = worldToScreenX(i * stepX);
          if (sx > 28 && sx < width - 28) {
            out.push(`  <text x="${f(sx)}" y="${f(labelY)}" fill="${escapeXml(colLabel)}" font-family="Roboto Mono, monospace" font-size="11" text-anchor="middle">${escapeXml(formatTick(i * stepX, piMode, stepX))}</text>`);
          }
        }
      }
      const labelX = Number.isFinite(ax) ? Math.min(Math.max(ax - 8, 42), width - 10) : 48;
      const iy0 = Math.floor(bounds.ymin / stepY);
      const iy1 = Math.ceil(bounds.ymax / stepY);
      if (Number.isFinite(iy0) && Number.isFinite(iy1) && iy1 - iy0 <= 200) {
        for (let j = iy0; j <= iy1; j++) {
          if (j === 0) continue;
          const sy = worldToScreenY(j * stepY);
          if (sy > 16 && sy < height - 16) {
            out.push(`  <text x="${f(labelX)}" y="${f(sy + 4)}" fill="${escapeXml(colLabel)}" font-family="Roboto Mono, monospace" font-size="11" text-anchor="end">${escapeXml(formatTick(j * stepY, false, stepY))}</text>`);
          }
        }
      }
    }

    const pushSvgPolyline = (points, col, lw, dashArr, opacity) => {
      const d = [];
      let prevPt = null;
      for (const pt of points) {
        if (pt === null) { prevPt = null; continue; }
        const sx = worldToScreenX(pt[0]);
        const sy = worldToScreenY(pt[1]);
        if (prevPt !== null) {
          const cl = clipSegment(prevPt[0], prevPt[1], sx, sy, -pad, -pad, width + pad, height + pad);
          if (cl) d.push(`M${f(cl[0])} ${f(cl[1])}L${f(cl[2])} ${f(cl[3])}`);
        }
        prevPt = [sx, sy];
      }
      if (d.length) {
        const dashAttr = dashArr && dashArr.length ? ` stroke-dasharray="${dashArr.join(" ")}"` : "";
        out.push(`  <path d="${d.join("")}" stroke="${col}" stroke-opacity="${opacity}" stroke-width="${lw}" stroke-linecap="round" stroke-linejoin="round" fill="none"${dashAttr} />`);
      }
    };

    for (const ex of expressions) {
      if (!ex.visible || !ex.result) continue;
      const res = ex.result;
      const col = getColor(ex.colorIdx);
      const st = getExprStyle(ex);

      if (res.kind === "point" && Array.isArray(res.point)) {
        const sx = worldToScreenX(res.point[0]);
        const sy = worldToScreenY(res.point[1]);
        if (sx >= -20 && sx <= width + 20 && sy >= -20 && sy <= height + 20) {
          out.push(`  <circle cx="${f(sx)}" cy="${f(sy)}" r="5.5" fill="${col}" fill-opacity="${st.opacity}" stroke="${dark ? "#09090b" : "#ffffff"}" stroke-width="2" />`);
        }
        continue;
      }

      if (res.kind === "table_points" && Array.isArray(res.points)) {
        for (const pt of res.points) {
          const sx = worldToScreenX(pt[0]);
          const sy = worldToScreenY(pt[1]);
          if (sx >= -20 && sx <= width + 20 && sy >= -20 && sy <= height + 20) {
            out.push(`  <circle cx="${f(sx)}" cy="${f(sy)}" r="5" fill="${col}" fill-opacity="${st.opacity}" stroke="${dark ? "#09090b" : "#ffffff"}" stroke-width="2" />`);
          }
        }
        continue;
      }

      if (res.kind === "curve_family" && Array.isArray(res.curves)) {
        res.curves.forEach((pts, idx) => {
          const fade = res.curves.length > 1 ? 0.42 + 0.58 * (idx / (res.curves.length - 1)) : 1;
          pushSvgPolyline(pts, col, Math.max(1.6, st.width * 0.85), st.dash, Number((st.opacity * fade).toFixed(2)));
        });
        continue;
      }

      if (res.kind === "slope_field" && Array.isArray(res.arrows)) {
        const segLen = Math.min(26, Math.max(12, Math.min(width / 26, height / 20) * 0.62));
        const half = segLen * 0.5;
        const d = [];
        for (const a of res.arrows) {
          const sx = worldToScreenX(a[0]);
          const sy = worldToScreenY(a[1]);
          const m = a[2];
          if (!Number.isFinite(sx) || !Number.isFinite(sy) || !Number.isFinite(m)) continue;
          const norm = Math.hypot(1, m);
          const ux = 1 / norm;
          const uy = -m / norm;
          const x0 = sx - ux * half, y0 = sy - uy * half;
          const x1 = sx + ux * half, y1 = sy + uy * half;
          d.push(`M${f(x0)} ${f(y0)}L${f(x1)} ${f(y1)}`);
          const head = 4.2;
          const ax1 = x1 - head * (ux * 0.85 - uy * 0.52);
          const ay1 = y1 - head * (uy * 0.85 + ux * 0.52);
          const ax2 = x1 - head * (ux * 0.85 + uy * 0.52);
          const ay2 = y1 - head * (uy * 0.85 - ux * 0.52);
          d.push(`M${f(ax1)} ${f(ay1)}L${f(x1)} ${f(y1)}L${f(ax2)} ${f(ay2)}`);
        }
        if (d.length) {
          out.push(`  <path d="${d.join("")}" stroke="${col}" stroke-opacity="${Number((0.78 * st.opacity).toFixed(2))}" stroke-width="${f(Math.max(1.2, st.width * 0.65))}" stroke-linecap="round" fill="none" />`);
        }
        continue;
      }

      if (res.kind === "integral_area" && res.points?.length) {
        const y0Screen = Math.max(-pad, Math.min(height + pad, worldToScreenY(0)));
        const clampX = (v) => Math.max(-pad, Math.min(width + pad, v));
        const clampY = (v) => Math.max(-pad, Math.min(height + pad, v));
        let seg = [];
        const flushSvgArea = () => {
          if (seg.length >= 2) {
            const polyPts = [`${f(clampX(worldToScreenX(seg[0][0])))},${f(y0Screen)}`];
            for (const pt of seg) polyPts.push(`${f(clampX(worldToScreenX(pt[0])))},${f(clampY(worldToScreenY(pt[1])))}`);
            polyPts.push(`${f(clampX(worldToScreenX(seg[seg.length - 1][0])))},${f(y0Screen)}`);
            out.push(`  <polygon points="${polyPts.join(" ")}" fill="${col}" fill-opacity="${Number((0.22 * st.opacity).toFixed(2))}" />`);
          }
          seg = [];
        };
        for (const pt of res.points) {
          if (pt === null) flushSvgArea();
          else seg.push(pt);
        }
        flushSvgArea();
        pushSvgPolyline(res.points, col, st.width, st.dash, st.opacity);
        continue;
      }

      if ((res.kind === "curve" || res.kind === "regression") && res.points?.length) {
        if (res.inequality) {
          const edgeY = res.inequality === "above" ? -10 : height + 10;
          const clampX = (v) => Math.max(-pad, Math.min(width + pad, v));
          const clampY = (v) => Math.max(-pad, Math.min(height + pad, v));
          let seg = [];
          const flushIneq = () => {
            if (seg.length >= 2) {
              const polyPts = [`${f(clampX(worldToScreenX(seg[0][0])))},${f(edgeY)}`];
              for (const pt of seg) polyPts.push(`${f(clampX(worldToScreenX(pt[0])))},${f(clampY(worldToScreenY(pt[1])))}`);
              polyPts.push(`${f(clampX(worldToScreenX(seg[seg.length - 1][0])))},${f(edgeY)}`);
              out.push(`  <polygon points="${polyPts.join(" ")}" fill="${col}" fill-opacity="${Number((0.14 * st.opacity).toFixed(2))}" />`);
            }
            seg = [];
          };
          for (const pt of res.points) {
            if (pt === null) flushIneq();
            else seg.push(pt);
          }
          flushIneq();
        }
        const effDash = res.strict && st.dash.length === 0 ? [6, 6] : st.dash;
        pushSvgPolyline(res.points, col, st.width, effDash, st.opacity);
        continue;
      }

      if (res.kind === "rect_region") {
        const x0 = res.x_lo !== null ? worldToScreenX(res.x_lo) : -pad;
        const x1 = res.x_hi !== null ? worldToScreenX(res.x_hi) : width + pad;
        const yTop = res.y_hi !== null ? worldToScreenY(res.y_hi) : -pad;
        const yBot = res.y_lo !== null ? worldToScreenY(res.y_lo) : height + pad;
        const rx = Math.max(-pad, Math.min(width + pad, Math.min(x0, x1)));
        const ry = Math.max(-pad, Math.min(height + pad, Math.min(yTop, yBot)));
        const rw = Math.max(1.5, Math.max(-pad, Math.min(width + pad, Math.max(x0, x1))) - rx);
        const rh = Math.max(1.5, Math.max(-pad, Math.min(height + pad, Math.max(yTop, yBot))) - ry);
        out.push(`  <rect x="${f(rx)}" y="${f(ry)}" width="${f(rw)}" height="${f(rh)}" fill="${col}" fill-opacity="${Number((0.2 * st.opacity).toFixed(2))}" stroke="${col}" stroke-opacity="${st.opacity}" stroke-width="${Math.max(1.5, st.width * 0.8)}" />`);
        continue;
      }

      if (res.kind === "implicit") {
        if (res.shade) {
          const { w, h, bits, bounds: sb } = res.shade;
          const off = document.createElement("canvas");
          off.width = w; off.height = h;
          const octx = off.getContext("2d");
          const img = octx.createImageData(w, h);
          const r = parseInt(col.slice(1, 3), 16);
          const g = parseInt(col.slice(3, 5), 16);
          const b = parseInt(col.slice(5, 7), 16);
          const a = Math.round((dark ? 38 : 34) * st.opacity);
          for (let i = 0; i < bits.length; i++) {
            if (bits[i] === "1") {
              const p = i * 4;
              img.data[p] = r; img.data[p + 1] = g; img.data[p + 2] = b; img.data[p + 3] = a;
            }
          }
          octx.putImageData(img, 0, 0);
          const dataUrl = off.toDataURL("image/png");
          if (sb && sb.length === 4) {
            const xL = worldToScreenX(sb[0]), xR = worldToScreenX(sb[1]);
            const yT = worldToScreenY(sb[3]), yB = worldToScreenY(sb[2]);
            if (Number.isFinite(xL) && Number.isFinite(xR) && Number.isFinite(yT) && Number.isFinite(yB)) {
              out.push(`  <image href="${dataUrl}" x="${f(xL)}" y="${f(yT)}" width="${f(xR - xL)}" height="${f(yB - yT)}" preserveAspectRatio="none" />`);
            }
          } else {
            out.push(`  <image href="${dataUrl}" x="0" y="0" width="${width}" height="${height}" preserveAspectRatio="none" />`);
          }
        }
        if (res.segments?.length) {
        const d = [];
        for (const s of res.segments) {
          const cl = clipSegment(
            worldToScreenX(s[0]), worldToScreenY(s[1]),
            worldToScreenX(s[2]), worldToScreenY(s[3]),
            -pad, -pad, width + pad, height + pad
          );
          if (cl) d.push(`M${f(cl[0])} ${f(cl[1])}L${f(cl[2])} ${f(cl[3])}`);
        }
        if (d.length) {
          const effDash = res.strict && st.dash.length === 0 ? [6, 6] : st.dash;
          const dashAttr = effDash.length ? ` stroke-dasharray="${effDash.join(" ")}"` : "";
          out.push(`  <path d="${d.join("")}" stroke="${col}" stroke-opacity="${st.opacity}" stroke-width="${st.width}" stroke-linecap="round" fill="none"${dashAttr} />`);
        }
        }
      }
    }

    out.push("</svg>");
    return out.join("\n");
  }

  let isDragging = false;
  let dragMoved = false;
  let dragStart = { x: 0, y: 0, cx: 0, cy: 0, yaw: 0, pitch: 0 };

  function findNearbyKeyPoint(clientX, clientY) {
    if (mode3D) return null;
    const candidates = [...getActiveKeyPoints()];
    for (const ex of expressions) {
      if (ex.visible && ex.result?.kind === "point" && Array.isArray(ex.result.point)) {
        candidates.push({
          x: ex.result.point[0],
          y: ex.result.point[1],
          type: "point",
          color: getColor(ex.colorIdx),
        });
      }
    }
    let best = null;
    let bestDist = 14;
    for (const kp of candidates) {
      const sx = worldToScreenX(kp.x);
      const sy = worldToScreenY(kp.y);
      const dist = Math.hypot(sx - clientX, sy - clientY);
      if (dist < bestDist) {
        bestDist = dist;
        best = kp;
      }
    }
    return best;
  }

  canvas.addEventListener("mousedown", (e) => {
    isDragging = true;
    dragMoved = false;
    dragStart = { x: e.clientX, y: e.clientY, cx: view.cx, cy: view.cy, yaw: cam3D.yaw, pitch: cam3D.pitch };
    tracePoint = null;
    tracePill.classList.remove("visible");
  });

  window.addEventListener("mousemove", (e) => {
    if (!mode3D) {
      hudX.textContent = formatHudCoord(screenToWorldX(e.clientX));
      hudY.textContent = formatHudCoord(screenToWorldY(e.clientY));
    }

    if (isDragging) {
      if (Math.hypot(e.clientX - dragStart.x, e.clientY - dragStart.y) > 4) dragMoved = true;
      if (mode3D) {
        cam3D.yaw = dragStart.yaw + (e.clientX - dragStart.x) * 0.008;
        cam3D.pitch = Math.max(-1.45, Math.min(1.45, dragStart.pitch + (e.clientY - dragStart.y) * 0.008));
        drawScene();
      } else {
        view.cx = dragStart.cx - (e.clientX - dragStart.x) / view.scale;
        view.cy = dragStart.cy + (e.clientY - dragStart.y) / view.scale;
        drawScene();
        requestComputeLive();
      }
      return;
    }

    if (mode3D || e.target !== canvas) {
      canvas.classList.remove("kp-hover");
      if (tracePoint || hoveredKeyPoint) {
        tracePoint = null;
        hoveredKeyPoint = null;
        tracePill.classList.remove("visible");
        drawScene();
      }
      return;
    }

    const nearKp = findNearbyKeyPoint(e.clientX, e.clientY);
    if (nearKp) {
      hoveredKeyPoint = nearKp;
      tracePoint = null;
      canvas.classList.add("kp-hover");
      tracePill.style.left = worldToScreenX(nearKp.x) + "px";
      tracePill.style.top = worldToScreenY(nearKp.y) + "px";
      const label = KP_LABELS[nearKp.type] || "";
      tracePill.innerHTML = `<span class="trace-math"></span>${label ? `<span class="trace-badge">${label}</span>` : ""}`;
      renderLatex(
        tracePill.querySelector(".trace-math"),
        `(${formatHudCoord(nearKp.x).replace("−", "-")},\\; ${formatHudCoord(nearKp.y).replace("−", "-")})`
      );
      tracePill.classList.add("visible");
      drawScene();
      return;
    }

    if (hoveredKeyPoint) {
      hoveredKeyPoint = null;
      canvas.classList.remove("kp-hover");
    }

    let best = null;
    let bestDist = 17;
    for (const ex of expressions) {
      if (!ex.visible || !ex.result) continue;
      if ((ex.result.kind === "curve" || ex.result.kind === "regression") && ex.result.points) {
        const col = getColor(ex.colorIdx);
        const pts = ex.result.points;
        for (let i = 0; i < pts.length; i++) {
          const pt = pts[i];
          if (!pt) continue;
          const sx = worldToScreenX(pt[0]);
          const sy = worldToScreenY(pt[1]);
          if (sx < -20 || sx > width + 20 || sy < -20 || sy > height + 20) continue;
          const dist = Math.hypot(sx - e.clientX, sy - e.clientY);
          if (dist < bestDist) {
            bestDist = dist;
            let slope = NaN;
            const prev = i > 0 ? pts[i - 1] : null;
            const next = i + 1 < pts.length ? pts[i + 1] : null;
            if (prev && next && Math.abs(next[0] - prev[0]) > 1e-12) {
              slope = (next[1] - prev[1]) / (next[0] - prev[0]);
            } else if (next && Math.abs(next[0] - pt[0]) > 1e-12) {
              slope = (next[1] - pt[1]) / (next[0] - pt[0]);
            } else if (prev && Math.abs(pt[0] - prev[0]) > 1e-12) {
              slope = (pt[1] - prev[1]) / (pt[0] - prev[0]);
            }
            best = { x: pt[0], y: pt[1], color: col, slope };
          }
        }
      }
    }

    if (best) {
      tracePoint = best;
      tracePill.style.left = worldToScreenX(best.x) + "px";
      tracePill.style.top = worldToScreenY(best.y) + "px";
      let tex = `(${formatHudCoord(best.x).replace("−", "-")},\\; ${formatHudCoord(best.y).replace("−", "-")})`;
      if (settings.showTangent && Number.isFinite(best.slope)) {
        tex += `\\quad f' = ${formatHudCoord(best.slope).replace("−", "-")}`;
      }
      renderLatex(tracePill, tex);
      tracePill.classList.add("visible");
      drawScene();
    } else if (tracePoint) {
      tracePoint = null;
      tracePill.classList.remove("visible");
      drawScene();
    }
  });

  window.addEventListener("mouseup", (e) => {
    const wasDragging = isDragging;
    isDragging = false;
    if (wasDragging && !dragMoved && !mode3D && e.target === canvas) {
      const clickedKp = findNearbyKeyPoint(e.clientX, e.clientY);
      if (clickedKp) {
        const existingIdx = pinnedKeyPoints.findIndex(
          (p) => Math.abs(p.x - clickedKp.x) < 1e-5 && Math.abs(p.y - clickedKp.y) < 1e-5
        );
        if (existingIdx >= 0) pinnedKeyPoints.splice(existingIdx, 1);
        else pinnedKeyPoints.push(clickedKp);
        drawScene();
      } else if (pinnedKeyPoints.length > 0) {
        pinnedKeyPoints = [];
        drawScene();
      }
    }
  });

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    if (mode3D) {
      const zf = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      cam3D.zoom = Math.max(0.25, Math.min(6.0, cam3D.zoom * zf));
      drawScene();
      return;
    }
    const zoomFactor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    const wx = screenToWorldX(e.clientX);
    const wy = screenToWorldY(e.clientY);
    view.scale = Math.min(Math.max(view.scale * zoomFactor, MIN_SCALE), MAX_SCALE);
    view.cx = wx - (e.clientX - width / 2) / view.scale;
    view.cy = wy + (e.clientY - height / 2) / view.scale;
    updateZoomHud();
    drawScene();
    requestComputeLive();
  }, { passive: false });
"""


def get_canvas_css() -> str:
    return CANVAS_CSS


def get_canvas_html() -> str:
    return CANVAS_HTML


def get_canvas_js() -> str:
    return CANVAS_JS

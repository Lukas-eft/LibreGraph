from __future__ import annotations

import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from math_engine.evaluator import evaluate_all_expressions
from ui.canvas import get_canvas_css, get_canvas_html, get_canvas_js
from ui.sidebar import get_sidebar_css, get_sidebar_html, get_sidebar_js
from utils.config import (
    APP_CONFIG,
    DEFAULT_SETTINGS,
    PALETTE_DARK,
    PALETTE_LIGHT,
    VIEWPORT_CONFIG,
)

MATHLIVE_LOADER_JS = r"""
<script>
  window.__mathLiveLoaded = false;
  window.__mathLiveReady = new Promise((resolve) => {
    const urls = [
      "https://cdn.jsdelivr.net/npm/mathlive",
      "https://unpkg.com/mathlive",
      "https://cdn.jsdelivr.net/npm/mathlive@0.101.2/dist/mathlive.min.js",
    ];
    let idx = 0;
    function finish(ok) {
      window.__mathLiveLoaded = ok;
      resolve(ok);
    }
    function tryLoad() {
      if (customElements.get("math-field")) {
        finish(true);
        return;
      }
      if (idx >= urls.length) {
        finish(false);
        return;
      }
      const s = document.createElement("script");
      s.src = urls[idx++];
      s.async = true;
      s.onload = () => {
        if (customElements.get("math-field")) {
          finish(true);
        } else {
          Promise.race([
            customElements.whenDefined("math-field").then(() => true),
            new Promise((r) => setTimeout(() => r(Boolean(customElements.get("math-field"))), 1500)),
          ]).then((ok) => {
            if (ok) finish(true);
            else tryLoad();
          });
        }
      };
      s.onerror = tryLoad;
      document.head.appendChild(s);
    }
    tryLoad();
  });
</script>
"""

THEME_CSS = r"""
  :root {
    --font-sans: "Roboto", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --font-mono: "Roboto Mono", ui-monospace, Menlo, monospace;

    --background: #09090b;
    --foreground: #fafafa;
    --muted-foreground: #a1a1aa;
    --subtle-foreground: #71717a;
    --primary: #fafafa;
    --primary-foreground: #18181b;
    --secondary: #27272a;
    --border: rgba(255, 255, 255, 0.09);
    --border-strong: rgba(255, 255, 255, 0.16);
    --ring: rgba(212, 212, 216, 0.35);
    --destructive: #ef4444;
    --destructive-bg: rgba(239, 68, 68, 0.12);
    --destructive-border: rgba(239, 68, 68, 0.28);

    --glass-panel: linear-gradient(160deg, rgba(32, 32, 36, 0.78) 0%, rgba(16, 16, 19, 0.86) 100%);
    --glass-card: linear-gradient(155deg, rgba(39, 39, 42, 0.56) 0%, rgba(24, 24, 27, 0.48) 100%);
    --glass-card-hover: linear-gradient(155deg, rgba(48, 48, 54, 0.66) 0%, rgba(28, 28, 32, 0.62) 100%);
    --glass-card-active: linear-gradient(155deg, rgba(63, 63, 70, 0.54) 0%, rgba(28, 28, 32, 0.72) 100%);
    --glass-control: rgba(24, 24, 27, 0.72);
    --glass-control-hover: rgba(39, 39, 42, 0.88);
    --key-num: rgba(39, 39, 42, 0.78);
    --key-num-hover: rgba(63, 63, 70, 0.88);
    --key-op: rgba(52, 52, 58, 0.72);
    --input-bg: rgba(9, 9, 11, 0.66);

    --math-selection-bg: rgba(250, 250, 250, 0.22);
    --math-contains-bg: rgba(255, 255, 255, 0.06);

    --glass-specular: inset 0 1px 0 rgba(255, 255, 255, 0.10), inset 0 -1px 0 rgba(0, 0, 0, 0.35);
    --glass-shadow: 0 24px 60px -12px rgba(0, 0, 0, 0.78), 0 4px 16px -2px rgba(0, 0, 0, 0.45);

    --sheen-1: rgba(255, 255, 255, 0.042);
    --sheen-2: rgba(161, 161, 170, 0.035);
    --sheen-3: rgba(82, 82, 91, 0.045);

    --grid-minor: rgba(255, 255, 255, 0.032);
    --grid-major: rgba(255, 255, 255, 0.085);
    --grid-axis: rgba(212, 212, 216, 0.42);
    --grid-label: rgba(161, 161, 170, 0.82);

    --slider-track: #27272a;
    --slider-fill: #e4e4e7;
    --slider-thumb: #fafafa;
    --switch-off: #27272a;
    --switch-on: #fafafa;
    --switch-thumb-off: #a1a1aa;
    --switch-thumb-on: #09090b;
  }

  [data-theme="light"] {
    --background: #f4f4f5;
    --foreground: #09090b;
    --muted-foreground: #52525b;
    --subtle-foreground: #71717a;
    --primary: #18181b;
    --primary-foreground: #fafafa;
    --secondary: #e4e4e7;
    --border: rgba(24, 24, 27, 0.09);
    --border-strong: rgba(24, 24, 27, 0.17);
    --ring: rgba(24, 24, 27, 0.22);
    --destructive: #dc2626;
    --destructive-bg: rgba(220, 38, 38, 0.08);
    --destructive-border: rgba(220, 38, 38, 0.24);

    --glass-panel: linear-gradient(160deg, rgba(255, 255, 255, 0.82) 0%, rgba(244, 244, 245, 0.74) 100%);
    --glass-card: linear-gradient(155deg, rgba(255, 255, 255, 0.82) 0%, rgba(244, 244, 245, 0.65) 100%);
    --glass-card-hover: linear-gradient(155deg, rgba(255, 255, 255, 0.94) 0%, rgba(244, 244, 245, 0.82) 100%);
    --glass-card-active: linear-gradient(155deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 250, 250, 0.90) 100%);
    --glass-control: rgba(255, 255, 255, 0.74);
    --glass-control-hover: rgba(255, 255, 255, 0.95);
    --key-num: rgba(255, 255, 255, 0.90);
    --key-num-hover: #ffffff;
    --key-op: rgba(228, 228, 231, 0.75);
    --input-bg: rgba(244, 244, 245, 0.88);

    --math-selection-bg: rgba(24, 24, 27, 0.16);
    --math-contains-bg: rgba(24, 24, 27, 0.05);

    --glass-specular: inset 0 1px 0 rgba(255, 255, 255, 0.95), inset 0 -1px 0 rgba(24, 24, 27, 0.04);
    --glass-shadow: 0 20px 50px -12px rgba(24, 24, 27, 0.14), 0 4px 14px -2px rgba(24, 24, 27, 0.06);

    --sheen-1: rgba(255, 255, 255, 0.65);
    --sheen-2: rgba(212, 212, 216, 0.45);
    --sheen-3: rgba(161, 161, 170, 0.22);

    --grid-minor: rgba(24, 24, 27, 0.045);
    --grid-major: rgba(24, 24, 27, 0.105);
    --grid-axis: rgba(24, 24, 27, 0.45);
    --grid-label: rgba(82, 82, 91, 0.85);

    --slider-track: #d4d4d8;
    --slider-fill: #18181b;
    --slider-thumb: #18181b;
    --switch-off: #d4d4d8;
    --switch-on: #18181b;
    --switch-thumb-off: #ffffff;
    --switch-thumb-on: #fafafa;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    width: 100%; height: 100%; overflow: hidden;
    font-family: var(--font-sans);
    background: var(--background);
    color: var(--foreground);
    user-select: none;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  .monochrome-atmosphere {
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background:
      radial-gradient(55vw 55vh at 16% 14%, var(--sheen-1), transparent 72%),
      radial-gradient(50vw 50vh at 84% 22%, var(--sheen-2), transparent 70%),
      radial-gradient(60vw 50vh at 50% 94%, var(--sheen-3), transparent 72%);
  }

  .liquid-glass {
    background: var(--glass-panel);
    backdrop-filter: blur(28px) saturate(140%);
    -webkit-backdrop-filter: blur(28px) saturate(140%);
    border: 1px solid var(--border);
    box-shadow: var(--glass-shadow), var(--glass-specular);
  }

  .top-controls {
    position: fixed; top: 16px; right: 16px; z-index: 12;
    border-radius: 14px; padding: 5px; display: flex; align-items: center; gap: 4px;
  }
  .top-controls .btn { height: 32px; min-width: 32px; padding: 0 10px; }
  .toolbar-sep { width: 1px; height: 18px; background: var(--border); margin: 0 2px; }

  .settings-popover {
    position: fixed; top: 64px; right: 16px; z-index: 20; width: 288px;
    border-radius: 16px; padding: 12px 14px; display: flex; flex-direction: column; gap: 11px;
    transform-origin: top right;
    transition: opacity 0.16s ease, transform 0.18s cubic-bezier(0.22, 1, 0.36, 1);
  }
  .settings-popover.hidden { opacity: 0; transform: translateY(-6px) scale(0.97); pointer-events: none; }
  .settings-title {
    font-size: 12.5px; font-weight: 500; letter-spacing: 0.01em;
    color: var(--muted-foreground); padding-bottom: 8px; border-bottom: 1px solid var(--border);
  }
  .setting-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .setting-info { display: flex; flex-direction: column; gap: 2px; }
  .setting-label { font-size: 13px; font-weight: 500; color: var(--foreground); }
  .setting-desc { font-size: 11px; color: var(--subtle-foreground); }

  .switch {
    position: relative; width: 36px; height: 20px; border-radius: 999px;
    border: 1px solid var(--border-strong); background: var(--switch-off);
    cursor: pointer; flex-shrink: 0; transition: background 0.16s ease, border-color 0.16s ease;
  }
  .switch::after {
    content: ""; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px;
    border-radius: 50%; background: var(--switch-thumb-off);
    transition: transform 0.18s cubic-bezier(0.22, 1, 0.36, 1), background 0.16s ease;
  }
  .switch.checked { background: var(--switch-on); border-color: transparent; }
  .switch.checked::after { transform: translateX(16px); background: var(--switch-thumb-on); }

  .export-toast {
    position: fixed; bottom: 64px; right: 16px; z-index: 30;
    padding: 8px 14px; border-radius: 12px;
    font-size: 12.5px; font-weight: 500; color: var(--foreground);
    opacity: 0; transform: translateY(8px); pointer-events: none;
    transition: opacity 0.18s ease, transform 0.2s cubic-bezier(0.22, 1, 0.36, 1);
  }
  .export-toast.visible { opacity: 1; transform: translateY(0); }
"""

TOOLBAR_AND_SETTINGS_HTML = r"""
  <div class="liquid-glass top-controls">
    <button id="mode3dBtn" class="btn" title="Zwischen 2D und 3D (z = f(x, y)) umschalten" style="font-family: var(--font-mono); font-size: 12px; padding: 0 9px;">2D</button>
    <div class="toolbar-sep"></div>
    <button id="undoBtn" class="btn" title="Rückgängig (Strg+Z)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11"/>
      </svg>
    </button>
    <button id="redoBtn" class="btn" title="Wiederholen (Strg+Y)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="m15 14 5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v0A5.5 5.5 0 0 0 9.5 20H13"/>
      </svg>
    </button>
    <div class="toolbar-sep"></div>
    <button id="zoomInBtn" class="btn" title="Hineinzoomen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/>
      </svg>
    </button>
    <button id="zoomOutBtn" class="btn" title="Herauszoomen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M8 11h6"/>
      </svg>
    </button>
    <button id="homeBtn" class="btn" title="Ansicht zurücksetzen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
      </svg>
    </button>
    <div class="toolbar-sep"></div>
    <button id="piAxisBtn" class="btn" title="x-Achse in π-Schritten" style="font-family: Georgia, serif; font-size: 14px;">π</button>
    <button id="exportPngBtn" class="btn" title="Als PNG exportieren">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>
      </svg>
      PNG
    </button>
    <button id="exportSvgBtn" class="btn" title="Als Vektor-SVG exportieren">
      SVG
    </button>
    <div class="toolbar-sep"></div>
    <button id="saveProjBtn" class="btn" title="Projekt speichern (.json)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
      </svg>
    </button>
    <button id="loadProjBtn" class="btn" title="Projekt laden (.json)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>
      </svg>
    </button>
    <input id="loadProjInput" type="file" accept=".json,application/json" style="display:none" />
    <button id="themeBtn" class="btn" title="Dark / Light Theme umschalten">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>
      </svg>
    </button>
    <button id="settingsBtn" class="btn" title="Einstellungen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
        <circle cx="12" cy="12" r="3"/>
      </svg>
    </button>
  </div>

  <div id="settingsPopover" class="liquid-glass settings-popover hidden">
    <div class="settings-title">Einstellungen</div>

    <div class="setting-row">
      <div class="setting-info">
        <span class="setting-label">Code-Eingabefeld</span>
        <span class="setting-desc">Rohes LaTeX-Feld unter der Formel</span>
      </div>
      <button id="swRawInput" class="switch checked" role="switch" aria-checked="true"></button>
    </div>

    <div class="setting-row">
      <div class="setting-info">
        <span class="setting-label">Auto-Slider</span>
        <span class="setting-desc">Unbekannte Variablen automatisch regeln</span>
      </div>
      <button id="swAutoSliders" class="switch checked" role="switch" aria-checked="true"></button>
    </div>

    <div class="setting-row">
      <div class="setting-info">
        <span class="setting-label">Koordinatengitter</span>
        <span class="setting-desc">Haupt- und Nebengitterlinien</span>
      </div>
      <button id="swGrid" class="switch checked" role="switch" aria-checked="true"></button>
    </div>

    <div class="setting-row">
      <div class="setting-info">
        <span class="setting-label">Polargitter</span>
        <span class="setting-desc">Konzentrische Kreise & Winkelstrahlen</span>
      </div>
      <button id="swPolarGrid" class="switch" role="switch" aria-checked="false"></button>
    </div>

    <div class="setting-row">
      <div class="setting-info">
        <span class="setting-label">Achsenbeschriftung</span>
        <span class="setting-desc">Zahlenwerte an x- und y-Achse</span>
      </div>
      <button id="swAxisLabels" class="switch checked" role="switch" aria-checked="true"></button>
    </div>

    <div class="setting-row">
      <div class="setting-info">
        <span class="setting-label">Nullstellen & Schnittpunkte</span>
        <span class="setting-desc">Anklickbare Punkte bei aktiver Funktion</span>
      </div>
      <button id="swKeyPoints" class="switch checked" role="switch" aria-checked="true"></button>
    </div>

    <div class="setting-row">
      <div class="setting-info">
        <span class="setting-label">Tangente am Cursor</span>
        <span class="setting-desc">Tangente & Steigung f'(x) beim Hovern</span>
      </div>
      <button id="swTangent" class="switch checked" role="switch" aria-checked="true"></button>
    </div>

    <div class="setting-row">
      <div class="setting-info">
        <span class="setting-label">Koordinaten-HUD</span>
        <span class="setting-desc">Mausposition & Zoom unten rechts</span>
      </div>
      <button id="swCoordHud" class="switch checked" role="switch" aria-checked="true"></button>
    </div>
  </div>

  <div id="exportToast" class="liquid-glass export-toast"></div>
"""

APP_STATE_JS = r"""

  function persistSettings() {
    try { localStorage.setItem("graph_settings_v4", JSON.stringify(settings)); } catch (_) {}
    saveAutoBackup();
  }

  const isLight = () => document.documentElement.getAttribute("data-theme") === "light";
  const getColor = (colorIdx) => {
    const pal = isLight() ? PALETTE_LIGHT : PALETTE_DARK;
    return pal[((colorIdx % pal.length) + pal.length) % pal.length];
  };

  let nextId = 1;
  let expressions = [
    { id: nextId++, type: "expr", raw: "", colorIdx: 0, visible: true, lineStyle: "solid", lineWidth: 2.4, opacity: 1.0, showTable: false, tableXs: [-2, -1, 0, 1, 2], folderId: null, result: null },
  ];

  const autoSliders = {};
  let activeExprId = expressions[0].id;
  let piMode = false;
  let mode3D = false;
  let currentTab = "basic";

  const historyStack = [];
  let historyIdx = -1;
  let historyTimer = null;

  function serializeProject() {
    return {
      version: 3,
      theme: document.documentElement.getAttribute("data-theme") || "dark",
      mode3D,
      piMode,
      view: { ...view },
      cam3D: { ...cam3D },
      settings: { ...settings },
      autoSliders: JSON.parse(JSON.stringify(autoSliders)),
      expressions: expressions.map((e) => ({
        id: e.id,
        type: e.type || "expr",
        raw: e.raw || "",
        text: e.text || "",
        title: e.title || "",
        collapsed: Boolean(e.collapsed),
        folderId: e.folderId ?? null,
        colorIdx: e.colorIdx ?? 0,
        visible: e.visible !== false,
        lineStyle: e.lineStyle || "solid",
        lineWidth: e.lineWidth ?? 2.4,
        opacity: e.opacity ?? 1.0,
        showTable: Boolean(e.showTable),
        tableXs: e.tableXs ? [...e.tableXs] : [-2, -1, 0, 1, 2],
        rows: e.rows ? e.rows.map((r) => [...r]) : undefined,
        min: e.min,
        max: e.max,
        step: e.step,
      })),
    };
  }

  function saveAutoBackup() {
    try { localStorage.setItem("graph_autosave_v1", JSON.stringify(serializeProject())); } catch (_) {}
  }

  function applyProjectState(proj, recordHistory = false) {
    if (!proj || !Array.isArray(proj.expressions) || proj.expressions.length === 0) return;
    expressions = proj.expressions.map((e) => ({
      ...e,
      type: e.type || "expr",
      result: null,
      playing: false,
    }));
    nextId = Math.max(1, ...expressions.map((e) => Number(e.id) || 0)) + 1;
    activeExprId = expressions[0].id;

    for (const k of Object.keys(autoSliders)) delete autoSliders[k];
    if (proj.autoSliders && typeof proj.autoSliders === "object") {
      for (const [k, v] of Object.entries(proj.autoSliders)) {
        autoSliders[k] = { ...v, playing: false };
      }
    }
    if (proj.view) {
      view.cx = Number(proj.view.cx) || 0;
      view.cy = Number(proj.view.cy) || 0;
      view.scale = Number(proj.view.scale) || DEFAULT_SCALE;
    }
    if (proj.cam3D) {
      cam3D.yaw = Number(proj.cam3D.yaw) || 0.68;
      cam3D.pitch = Number(proj.cam3D.pitch) || 0.52;
      cam3D.zoom = Number(proj.cam3D.zoom) || 1.0;
    }
    if (proj.settings) Object.assign(settings, proj.settings);
    if (proj.theme) document.documentElement.setAttribute("data-theme", proj.theme);
    if (typeof proj.piMode === "boolean") {
      piMode = proj.piMode;
      document.getElementById("piAxisBtn")?.classList.toggle("btn-ghost-active", piMode);
    }
    if (typeof proj.mode3D === "boolean") setMode3D(proj.mode3D, true);

    exprListEl.innerHTML = "";
    syncSettingsUI();
    syncExprCards();
    updateZoomHud();
    drawScene();
    scheduleCompute(15);
    if (recordHistory) pushHistory();
    else saveAutoBackup();
  }

  function pushHistory() {
    clearTimeout(historyTimer);
    const snap = JSON.stringify(serializeProject());
    if (historyIdx >= 0 && historyStack[historyIdx] === snap) {
      saveAutoBackup();
      return;
    }
    historyStack.splice(historyIdx + 1);
    historyStack.push(snap);
    if (historyStack.length > 60) historyStack.shift();
    historyIdx = historyStack.length - 1;
    saveAutoBackup();
  }

  function scheduleHistoryPush() {
    clearTimeout(historyTimer);
    historyTimer = setTimeout(pushHistory, 450);
  }

  function undoHistory() {
    if (historyIdx <= 0) return;
    historyIdx -= 1;
    applyProjectState(JSON.parse(historyStack[historyIdx]), false);
    showToast("Rückgängig");
  }

  function redoHistory() {
    if (historyIdx >= historyStack.length - 1) return;
    historyIdx += 1;
    applyProjectState(JSON.parse(historyStack[historyIdx]), false);
    showToast("Wiederholt");
  }

  const DEFAULT_SCALE = 72;
  const MIN_SCALE = 1e-250;
  const MAX_SCALE = 1e12;
  const view = { cx: 0, cy: 0, scale: DEFAULT_SCALE };

  const canvas = document.getElementById("graphCanvas");
  const ctx = canvas.getContext("2d");
  const exprListEl = document.getElementById("exprList");
  const tracePill = document.getElementById("tracePill");
  const coordHud = document.getElementById("coordHud");
  const hudX = document.getElementById("hudX");
  const hudY = document.getElementById("hudY");
  const hudZoom = document.getElementById("hudZoom");

  let dpr = window.devicePixelRatio || 1;
  let width = window.innerWidth;
  let height = window.innerHeight;
  let fetchTimer = null;
  let isFetching = false;
  let needsRefetch = false;
  let tracePoint = null;

  function renderLatex(el, tex) {
    if (!tex) { el.textContent = ""; return; }
    if (window.katex) {
      try {
        window.katex.render(tex, el, { throwOnError: false, displayMode: false });
        return;
      } catch (_) {}
    }
    el.textContent = tex;
  }

  const worldToScreenX = (x) => width / 2 + (x - view.cx) * view.scale;
  const worldToScreenY = (y) => height / 2 - (y - view.cy) * view.scale;
  const screenToWorldX = (sx) => view.cx + (sx - width / 2) / view.scale;
  const screenToWorldY = (sy) => view.cy - (sy - height / 2) / view.scale;

  function getBounds() {
    const clamp = (v) => Math.max(-1e290, Math.min(1e290, v));
    return {
      xmin: clamp(screenToWorldX(0)),
      xmax: clamp(screenToWorldX(width)),
      ymin: clamp(screenToWorldY(height)),
      ymax: clamp(screenToWorldY(0)),
    };
  }

  function formatCompactSci(val, sig = 3) {
    if (!Number.isFinite(val) || val === 0) return "0";
    const abs = Math.abs(val);
    if (abs >= 1e5 || abs < 1e-3) {
      return val.toExponential(Math.max(1, sig - 1)).replace("e+", "e").replace(/-/g, "−");
    }
    return String(Number(val.toPrecision(sig))).replace("-", "−");
  }

  function formatHudCoord(val) {
    if (!Number.isFinite(val)) return "0";
    const span = width / Math.max(view.scale, MIN_SCALE);
    if (Math.abs(val) < span * 1e-9) return "0";
    const abs = Math.abs(val);
    if (abs >= 1e6 || abs < 1e-3) {
      return val.toExponential(2).replace("e+", "e").replace(/-/g, "−");
    }
    const dec = span < 1 ? Math.min(6, Math.max(2, Math.ceil(-Math.log10(span)) + 2)) : 2;
    return val.toFixed(dec).replace("-", "−");
  }

  function updateZoomHud() {
    const ratio = view.scale / DEFAULT_SCALE;
    if (ratio >= 0.05 && ratio < 1000) {
      hudZoom.textContent = ratio.toFixed(ratio < 1 ? 2 : 1) + "×";
    } else {
      hudZoom.textContent = formatCompactSci(ratio, 2) + "×";
    }
  }

  function resizeCanvas() {
    dpr = window.devicePixelRatio || 1;
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    drawScene();
    scheduleCompute(50);
  }

  function collectExplicitParams() {
    const params = {};
    for (const ex of expressions) {
      if ((ex.type || "expr") !== "expr") continue;
      if (ex.result && ex.result.kind === "slider") {
        params[ex.result.name] = ex.result.value;
      } else {
        const rawStr = typeof ex.raw === "string" ? ex.raw.trim() : "";
        const m = rawStr.match(/^([a-zA-Z][a-zA-Z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?)$/);
        if (m) params[m[1]] = parseFloat(m[2]);
      }
    }
    return params;
  }

  function collectAutoParams() {
    const out = {};
    for (const [k, st] of Object.entries(autoSliders)) out[k] = st.value;
    return out;
  }

  function scheduleCompute(delayMs = 45) {
    clearTimeout(fetchTimer);
    fetchTimer = setTimeout(requestCompute, delayMs);
  }

  function requestComputeLive() {
    clearTimeout(fetchTimer);
    if (isFetching) {
      needsRefetch = true;
    } else {
      requestCompute();
    }
  }

  async function requestCompute() {
    if (isFetching) {
      needsRefetch = true;
      return;
    }
    isFetching = true;
    needsRefetch = false;

    try {
      const payload = {
        bounds: getBounds(),
        params: collectExplicitParams(),
        auto_params: collectAutoParams(),
        settings: { auto_sliders: settings.autoSliders, show_key_points: settings.showKeyPoints },
        expressions: expressions.map((e) => ({
          id: e.id,
          type: e.type || "expr",
          raw: e.raw || "",
          rows: e.type === "table" ? (e.rows || []) : undefined,
          visible: e.visible !== false,
          table_xs: e.showTable ? (e.tableXs || [-2, -1, 0, 1, 2]) : null,
        })),
      };
      const resp = await fetch("/api/eval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (resp.ok) {
        const data = await resp.json();
        const activeAutoVars = new Set();

        for (const item of data.results) {
          const ex = expressions.find((e) => e.id === item.id);
          if (!ex) continue;
          ex.result = item;

          if (item.kind === "slider" && ex.min === undefined) {
            ex.min = Math.min(-5, Math.floor(item.value - 5));
            ex.max = Math.max(5, Math.ceil(item.value + 5));
            ex.step = 0.05;
            ex.playing = false;
            ex.dir = 1;
          }

          if (settings.autoSliders && Array.isArray(item.auto_vars)) {
            for (const vname of item.auto_vars) {
              activeAutoVars.add(vname);
              if (!autoSliders[vname]) {
                autoSliders[vname] = { value: 1, min: -5, max: 5, step: 0.05, playing: false, dir: 1 };
              }
            }
          }
        }

        for (const key of Object.keys(autoSliders)) {
          if (!activeAutoVars.has(key)) delete autoSliders[key];
        }

        syncExprCards();
        drawScene();
      }
    } catch (err) {
      console.error(err);
    } finally {
      isFetching = false;
      if (needsRefetch) {
        needsRefetch = false;
        requestAnimationFrame(() => requestCompute());
      }
    }
  }

"""

APP_CONTROLS_JS = r"""
  const settingsBtn = document.getElementById("settingsBtn");
  const settingsPopover = document.getElementById("settingsPopover");
  const swRawInput = document.getElementById("swRawInput");
  const swAutoSliders = document.getElementById("swAutoSliders");
  const swGrid = document.getElementById("swGrid");
  const swPolarGrid = document.getElementById("swPolarGrid");
  const swAxisLabels = document.getElementById("swAxisLabels");
  const swKeyPoints = document.getElementById("swKeyPoints");
  const swTangent = document.getElementById("swTangent");
  const swCoordHud = document.getElementById("swCoordHud");
  const exportToast = document.getElementById("exportToast");
  let toastTimer = null;

  function showToast(msg) {
    exportToast.textContent = msg;
    exportToast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => exportToast.classList.remove("visible"), 2600);
  }

  function syncSettingsUI() {
    document.body.classList.toggle("hide-raw-input", !settings.showRawInput);
    coordHud.classList.toggle("hidden", !settings.showCoordHud);

    const setSwitch = (el, on) => {
      el.classList.toggle("checked", on);
      el.setAttribute("aria-checked", String(on));
    };
    setSwitch(swRawInput, settings.showRawInput);
    setSwitch(swAutoSliders, settings.autoSliders);
    setSwitch(swGrid, settings.showGrid);
    setSwitch(swPolarGrid, settings.polarGrid);
    setSwitch(swAxisLabels, settings.showAxisLabels);
    setSwitch(swKeyPoints, settings.showKeyPoints);
    setSwitch(swTangent, settings.showTangent);
    setSwitch(swCoordHud, settings.showCoordHud);
  }

  settingsBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const willOpen = settingsPopover.classList.contains("hidden");
    settingsPopover.classList.toggle("hidden", !willOpen);
    settingsBtn.classList.toggle("btn-ghost-active", willOpen);
  });

  document.addEventListener("mousedown", (e) => {
    if (
      !settingsPopover.classList.contains("hidden") &&
      !settingsPopover.contains(e.target) &&
      !settingsBtn.contains(e.target)
    ) {
      settingsPopover.classList.add("hidden");
      settingsBtn.classList.remove("btn-ghost-active");
    }
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !settingsPopover.classList.contains("hidden")) {
      settingsPopover.classList.add("hidden");
      settingsBtn.classList.remove("btn-ghost-active");
    }
  });

  swRawInput.addEventListener("click", () => {
    settings.showRawInput = !settings.showRawInput; persistSettings(); syncSettingsUI();
  });
  swAutoSliders.addEventListener("click", () => {
    settings.autoSliders = !settings.autoSliders; persistSettings(); syncSettingsUI(); scheduleCompute(10);
  });
  swGrid.addEventListener("click", () => {
    settings.showGrid = !settings.showGrid; persistSettings(); syncSettingsUI(); drawScene();
  });
  swPolarGrid.addEventListener("click", () => {
    settings.polarGrid = !settings.polarGrid; persistSettings(); syncSettingsUI(); drawScene();
  });
  swAxisLabels.addEventListener("click", () => {
    settings.showAxisLabels = !settings.showAxisLabels; persistSettings(); syncSettingsUI(); drawScene();
  });
  swKeyPoints.addEventListener("click", () => {
    settings.showKeyPoints = !settings.showKeyPoints; persistSettings(); syncSettingsUI();
    if (!settings.showKeyPoints) pinnedKeyPoints = [];
    scheduleCompute(10); drawScene();
  });
  swTangent.addEventListener("click", () => {
    settings.showTangent = !settings.showTangent; persistSettings(); syncSettingsUI(); drawScene();
  });
  swCoordHud.addEventListener("click", () => {
    settings.showCoordHud = !settings.showCoordHud; persistSettings(); syncSettingsUI();
  });

  document.getElementById("addExprBtn").addEventListener("click", (e) => {
    e.preventDefault(); e.stopPropagation(); addExpression("");
  });
  document.getElementById("addTableBtn").addEventListener("click", (e) => {
    e.preventDefault(); e.stopPropagation(); addStandaloneTable();
  });
  document.getElementById("addNoteBtn").addEventListener("click", (e) => {
    e.preventDefault(); e.stopPropagation(); addNote();
  });
  document.getElementById("addFolderBtn").addEventListener("click", (e) => {
    e.preventDefault(); e.stopPropagation(); addFolder();
  });

  const mode3dBtn = document.getElementById("mode3dBtn");
  function setMode3D(on, silent = false) {
    mode3D = Boolean(on);
    mode3dBtn.textContent = mode3D ? "3D" : "2D";
    mode3dBtn.classList.toggle("btn-ghost-active", mode3D);
    if (mode3D) {
      tracePoint = null;
      tracePill.classList.remove("visible");
    }
    syncExprCards();
    drawScene();
    if (!silent) saveAutoBackup();
  }
  mode3dBtn.addEventListener("click", () => setMode3D(!mode3D));

  document.getElementById("undoBtn").addEventListener("click", undoHistory);
  document.getElementById("redoBtn").addEventListener("click", redoHistory);
  window.addEventListener("keydown", (e) => {
    const mod = e.ctrlKey || e.metaKey;
    if (!mod) return;
    if (document.activeElement && (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA")) return;
    if (e.key.toLowerCase() === "z" && !e.shiftKey) {
      e.preventDefault(); undoHistory();
    } else if ((e.key.toLowerCase() === "z" && e.shiftKey) || e.key.toLowerCase() === "y") {
      e.preventDefault(); redoHistory();
    }
  });

  const sidebar = document.getElementById("sidebar");
  const openBtn = document.getElementById("openSidebarBtn");
  document.getElementById("collapseSidebarBtn").addEventListener("click", () => {
    sidebar.classList.add("collapsed"); openBtn.classList.remove("hidden");
  });
  openBtn.addEventListener("click", () => {
    sidebar.classList.remove("collapsed"); openBtn.classList.add("hidden");
  });

  document.getElementById("zoomInBtn").addEventListener("click", () => {
    view.scale = Math.min(view.scale * 1.45, MAX_SCALE);
    updateZoomHud(); drawScene(); requestComputeLive();
  });
  document.getElementById("zoomOutBtn").addEventListener("click", () => {
    view.scale = Math.max(view.scale / 1.45, MIN_SCALE);
    updateZoomHud(); drawScene(); requestComputeLive();
  });
  document.getElementById("homeBtn").addEventListener("click", () => {
    if (mode3D) {
      cam3D.yaw = 0.68; cam3D.pitch = 0.52; cam3D.zoom = 1.0;
      drawScene();
    } else {
      view.cx = 0; view.cy = 0; view.scale = DEFAULT_SCALE;
      updateZoomHud(); drawScene(); scheduleCompute(20);
    }
  });

  const piBtn = document.getElementById("piAxisBtn");
  piBtn.addEventListener("click", () => {
    piMode = !piMode;
    piBtn.classList.toggle("btn-ghost-active", piMode);
    saveAutoBackup();
    drawScene();
  });

  document.getElementById("themeBtn").addEventListener("click", () => {
    const html = document.documentElement;
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    try { localStorage.setItem("graph_theme_v1", next); } catch (_) {}
    saveAutoBackup();
    syncExprCards();
    drawScene();
  });

  async function triggerExport(format) {
    const filename = format === "svg" ? "graph.svg" : "graph.png";
    const content = format === "svg" ? buildSvgString() : buildPngDataUrl();

    try {
      const resp = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format, filename, content }),
      });
      if (resp.ok) {
        const info = await resp.json();
        if (info.saved) {
          showToast(`Gespeichert: ${info.name || filename}`);
          return;
        }
        if (info.cancelled) return;
      }
    } catch (_) {}

    let blob;
    if (format === "svg") {
      blob = new Blob([content], { type: "image/svg+xml;charset=utf-8" });
    } else {
      const b64 = content.split(",")[1] || "";
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      blob = new Blob([bytes], { type: "image/png" });
    }
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = filename;
    link.href = url;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
    showToast(`Exportiert: ${filename}`);
  }

  document.getElementById("exportPngBtn").addEventListener("click", () => triggerExport("png"));
  document.getElementById("exportSvgBtn").addEventListener("click", () => triggerExport("svg"));

  document.getElementById("saveProjBtn").addEventListener("click", async () => {
    const filename = "projekt.json";
    const jsonStr = JSON.stringify(serializeProject(), null, 2);
    try {
      const resp = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format: "json", filename, content: jsonStr }),
      });
      if (resp.ok) {
        const info = await resp.json();
        if (info.saved) { showToast(`Projekt gespeichert: ${info.name || filename}`); return; }
        if (info.cancelled) return;
      }
    } catch (_) {}
    const blob = new Blob([jsonStr], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = filename;
    link.href = url;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
    showToast(`Projekt exportiert: ${filename}`);
  });

  const loadProjInput = document.getElementById("loadProjInput");
  document.getElementById("loadProjBtn").addEventListener("click", async () => {
    try {
      const resp = await fetch("/api/project/load", { method: "POST" });
      if (resp.ok) {
        const info = await resp.json();
        if (info.loaded && info.project) {
          applyProjectState(info.project, true);
          showToast(`Projekt geladen: ${info.name || "projekt.json"}`);
          return;
        }
        if (info.cancelled) return;
      }
    } catch (_) {}
    loadProjInput.value = "";
    loadProjInput.click();
  });

  loadProjInput.addEventListener("change", () => {
    const file = loadProjInput.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const proj = JSON.parse(String(reader.result || ""));
        applyProjectState(proj, true);
        showToast(`Projekt geladen: ${file.name}`);
      } catch (_) {
        showToast("Ungültige Projektdatei");
      }
    };
    reader.readAsText(file);
  });

  document.getElementById("toggleKeypadBtn").addEventListener("click", () => {
    document.getElementById("keypadPanel").classList.toggle("collapsed");
  });

  window.addEventListener("resize", resizeCanvas);
  window.addEventListener("load", async () => {
    const ok = await Promise.race([
      window.__mathLiveReady,
      new Promise((r) => setTimeout(() => r(Boolean(window.__mathLiveLoaded)), 4000)),
    ]);
    document.body.classList.toggle("no-mathlive", !ok);
    try {
      if (ok && window.MathfieldElement) window.MathfieldElement.soundsDirectory = null;
    } catch (_) {}

    try {
      const savedTheme = localStorage.getItem("graph_theme_v1");
      if (savedTheme === "dark" || savedTheme === "light") {
        document.documentElement.setAttribute("data-theme", savedTheme);
      }
    } catch (_) {}
    syncSettingsUI();
    buildKeypad();
    let restored = false;
    try {
      const auto = JSON.parse(localStorage.getItem("graph_autosave_v1") || "null");
      if (auto && Array.isArray(auto.expressions) && auto.expressions.length > 0) {
        applyProjectState(auto, false);
        restored = true;
      }
    } catch (_) {}
    if (!restored) {
      syncExprCards();
      updateZoomHud();
    }
    pushHistory();
    resizeCanvas();

    if (ok) {
      const firstMf = exprListEl.querySelector(`math-field[data-mf-id="${activeExprId}"]`);
      if (firstMf) { try { firstMf.focus(); } catch (_) {} }
    } else {
      const firstInp = exprListEl.querySelector(`input[data-input-id="${activeExprId}"]`);
      if (firstInp) firstInp.focus();
    }
  });
"""


def build_html_page() -> str:
    config_js = f"""
  const PALETTE_DARK = {json.dumps(list(PALETTE_DARK))};
  const PALETTE_LIGHT = {json.dumps(list(PALETTE_LIGHT))};
  const settings = {json.dumps(DEFAULT_SETTINGS)};
  const DEFAULT_SCALE = {VIEWPORT_CONFIG.default_scale!r};
  const MIN_SCALE = {VIEWPORT_CONFIG.min_scale!r};
  const MAX_SCALE = {VIEWPORT_CONFIG.max_scale!r};
"""
    state_body = APP_STATE_JS
    for redundant in (
        "  const DEFAULT_SCALE = 72;\n",
        "  const MIN_SCALE = 1e-250;\n",
        "  const MAX_SCALE = 1e12;\n",
    ):
        state_body = state_body.replace(redundant, "")

    return f"""<!DOCTYPE html>
<html lang="de" data-theme="dark">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{APP_CONFIG.window_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" />
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
{MATHLIVE_LOADER_JS}
<style>
{THEME_CSS}
{get_canvas_css()}
{get_sidebar_css()}
</style>
</head>
<body>
  <div class="monochrome-atmosphere"></div>
{get_canvas_html()}
{get_sidebar_html()}
{TOOLBAR_AND_SETTINGS_HTML}
<script>
(() => {{
{config_js}
  try {{
    const saved = JSON.parse(localStorage.getItem("graph_settings_v4") || "null");
    if (saved && typeof saved === "object") Object.assign(settings, saved);
  }} catch (_) {{}}
{state_body}
{get_canvas_js()}
{get_sidebar_js()}
{APP_CONTROLS_JS}
}})();
</script>
</body>
</html>
"""


_WEBVIEW_WINDOW = None


def set_webview_window(window) -> None:
    global _WEBVIEW_WINDOW
    _WEBVIEW_WINDOW = window


def _save_via_webview(filename: str, fmt: str, raw_bytes: bytes) -> dict:
    win = _WEBVIEW_WINDOW
    if win is None:
        return {"fallback_download": True}
    try:
        import webview

        save_mode = getattr(getattr(webview, "FileDialog", None), "SAVE", None)
        if save_mode is None:
            save_mode = getattr(webview, "SAVE_DIALOG", 20)
        file_types = {"svg": ("SVG Vektorgrafik (*.svg)",), "json": ("JSON Projekt (*.json)",)}.get(fmt, ("PNG Bild (*.png)",))
        chosen = win.create_file_dialog(
            save_mode,
            save_filename=(Path(str(filename)).name or f"graph.{fmt}"),
            file_types=file_types,
        )
        if not chosen:
            return {"saved": False, "cancelled": True}
        out_path = chosen[0] if isinstance(chosen, (list, tuple)) else str(chosen)
        ext = f".{fmt}"
        if not out_path.lower().endswith(ext):
            out_path += ext
        Path(out_path).write_bytes(raw_bytes)
        return {"saved": True, "path": out_path, "name": Path(out_path).name}
    except Exception:
        dl_dir = Path.home() / "Downloads"
        dl_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(str(filename)).name or f"graph.{fmt}"
        if not safe_name.lower().endswith(f".{fmt}"):
            safe_name = f"{safe_name}.{fmt}"
        out_path = dl_dir / safe_name
        out_path.write_bytes(raw_bytes)
        return {"saved": True, "path": str(out_path), "name": out_path.name}


class MathAppHandler(BaseHTTPRequestHandler):

    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            body = build_html_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/project/load":
            try:
                win = _WEBVIEW_WINDOW
                if win is None:
                    res = {"fallback_upload": True}
                else:
                    import webview

                    open_mode = getattr(getattr(webview, "FileDialog", None), "OPEN", None)
                    if open_mode is None:
                        open_mode = getattr(webview, "OPEN_DIALOG", 10)
                    chosen = win.create_file_dialog(open_mode, file_types=("JSON Projekt (*.json)",))
                    if not chosen:
                        res = {"loaded": False, "cancelled": True}
                    else:
                        in_path = Path(chosen[0] if isinstance(chosen, (list, tuple)) else str(chosen))
                        proj = json.loads(in_path.read_text(encoding="utf-8"))
                        res = {"loaded": True, "name": in_path.name, "project": proj}
                out = json.dumps(res).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)
            except Exception as exc:
                err = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err)))
                self.end_headers()
                self.wfile.write(err)
            return

        if self.path == "/api/export":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                fmt = data.get("format", "png")
                if fmt not in ("svg", "png", "json"):
                    fmt = "png"
                filename = data.get("filename") or f"graph.{fmt}"
                content = data.get("content", "")
                if fmt in ("svg", "json"):
                    raw_bytes = content.encode("utf-8")
                else:
                    b64 = content.split(",", 1)[1] if "," in content else content
                    raw_bytes = base64.b64decode(b64)
                res = _save_via_webview(filename, fmt, raw_bytes)
                out = json.dumps(res).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)
            except Exception as exc:
                err = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err)))
                self.end_headers()
                self.wfile.write(err)
            return

        if self.path != "/api/eval":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            data = json.loads(raw_body.decode("utf-8"))

            results = evaluate_all_expressions(
                items=data.get("expressions", []),
                explicit_params=data.get("params", {}),
                auto_params=data.get("auto_params", {}),
                bounds=data["bounds"],
                settings=data.get("settings", {}),
            )

            out = json.dumps({"results": results}, allow_nan=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except Exception as exc:
            err = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)


def create_app_server(host: str = APP_CONFIG.host, port: int = APP_CONFIG.port) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), MathAppHandler)

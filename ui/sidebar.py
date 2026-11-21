from __future__ import annotations

SIDEBAR_CSS = r"""
  .sidebar {
    position: fixed; top: 16px; left: 16px; bottom: 16px;
    width: 392px; max-width: calc(100vw - 32px);
    border-radius: 20px; z-index: 10;
    display: flex; flex-direction: column;
    transition: transform 0.34s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.22s ease;
    overflow: hidden;
  }
  .sidebar.collapsed {
    transform: translateX(calc(-100% - 24px));
    opacity: 0; pointer-events: none;
  }

  .sidebar-header {
    padding: 12px; display: flex; align-items: center; gap: 8px;
    border-bottom: 1px solid var(--border);
  }

  .btn {
    height: 34px; min-width: 34px; padding: 0 11px;
    border-radius: 10px; border: 1px solid var(--border);
    background: var(--glass-control); color: var(--foreground);
    font-family: var(--font-sans); font-size: 13px; font-weight: 500;
    cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
    transition: background 0.15s ease, border-color 0.15s ease, transform 0.12s ease, color 0.15s ease;
  }
  .btn:hover { background: var(--glass-control-hover); border-color: var(--border-strong); }
  .btn:active { transform: scale(0.97); }
  .btn svg { width: 15px; height: 15px; stroke-width: 1.85; flex-shrink: 0; }

  .btn-primary {
    background: var(--primary); color: var(--primary-foreground); border-color: transparent;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255,255,255,0.4);
  }
  .btn-primary:hover { background: var(--primary); opacity: 0.9; border-color: transparent; }
  .btn-add-full { flex: 1; }
  .btn-ghost-active { background: var(--primary); color: var(--primary-foreground); border-color: transparent; }
  .btn-ghost-active:hover { background: var(--primary); opacity: 0.92; }

  .expr-list {
    flex: 1; overflow-y: auto; padding: 12px;
    display: flex; flex-direction: column; gap: 9px;
  }
  .expr-list::-webkit-scrollbar { width: 5px; }
  .expr-list::-webkit-scrollbar-thumb { background: rgba(161, 161, 170, 0.22); border-radius: 99px; }
  .expr-list::-webkit-scrollbar-thumb:hover { background: rgba(161, 161, 170, 0.38); }

  .expr-card {
    border-radius: 14px; background: var(--glass-card);
    border: 1px solid var(--border);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.055);
    padding: 10px 11px; position: relative;
    transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
  }
  .expr-card:hover { background: var(--glass-card-hover); }
  .expr-card.focused {
    background: var(--glass-card-active); border-color: var(--border-strong);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.10);
  }

  .expr-top { display: flex; align-items: flex-start; gap: 10px; }
  .expr-gutter {
    display: flex; flex-direction: column; align-items: center; gap: 7px;
    padding-top: 3px; min-width: 26px;
  }
  .expr-num { font-size: 10.5px; color: var(--subtle-foreground); font-family: var(--font-mono); font-weight: 500; }

  .color-dot {
    width: 20px; height: 20px; border-radius: 999px;
    border: 2px solid rgba(255, 255, 255, 0.24);
    cursor: pointer; position: relative;
    transition: transform 0.14s ease, opacity 0.14s ease, border-color 0.14s ease;
  }
  .color-dot:hover { transform: scale(1.12); border-color: rgba(255, 255, 255, 0.65); }
  .color-dot.hidden-curve {
    background: transparent !important; box-shadow: none !important;
    border: 1.5px dashed var(--subtle-foreground); opacity: 0.65;
  }

  .expr-body { flex: 1; min-width: 0; position: relative; user-select: text; -webkit-user-select: text; }

  .math-editor-wrap {
    position: relative; min-height: 29px; padding: 0 2px 4px;
    display: flex; align-items: center; cursor: text;
    user-select: text; -webkit-user-select: text;
  }
  body.hide-raw-input .math-editor-wrap { min-height: 38px; padding: 4px 2px; }

  .math-placeholder {
    position: absolute; left: 4px; top: 50%; transform: translateY(-50%);
    pointer-events: none; color: var(--subtle-foreground);
    font-family: var(--font-sans); font-size: 0.88rem; opacity: 0.9;
    transition: opacity 0.12s ease;
  }
  .math-editor-wrap.has-value .math-placeholder { opacity: 0; }

  math-field.math-editor {
    display: block; width: 100%; min-height: 28px;
    background: transparent !important; background-color: transparent !important;
    border: none !important; border-radius: 0 !important;
    box-shadow: none !important; outline: none !important;
    padding: 0 !important; margin: 0 !important;
    color: var(--foreground) !important; font-size: 1.08rem; line-height: 1.35;
    cursor: text; user-select: text; -webkit-user-select: text;
    --background: transparent;
    --caret-color: var(--foreground);
    --selection-background-color: var(--math-selection-bg);
    --selection-color: var(--foreground);
    --contains-highlight-background-color: var(--math-contains-bg);
    --primary-color: var(--foreground);
    --smart-fence-opacity: 0.45;
  }
  math-field.math-editor:focus, math-field.math-editor:focus-within {
    outline: none !important; border: none !important; box-shadow: none !important;
  }
  math-field.math-editor::part(container) {
    background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important;
  }
  math-field.math-editor::part(content) { padding: 2px 2px !important; }
  math-field.math-editor::part(virtual-keyboard-toggle),
  math-field.math-editor::part(menu-toggle) { display: none !important; }

  .latex-fallback {
    display: none; width: 100%; min-height: 27px; padding: 1px 3px 4px;
    font-size: 1.04rem; color: var(--foreground); overflow-x: auto; overflow-y: hidden; white-space: nowrap;
  }
  body.no-mathlive math-field.math-editor { display: none !important; }
  body.no-mathlive .latex-fallback { display: block; }

  .expr-input {
    width: 100%; margin-top: 2px; background: var(--input-bg);
    border: 1px solid var(--border); border-radius: 9px; padding: 7px 10px;
    color: var(--foreground); font-family: var(--font-mono); font-size: 12.5px;
    outline: none; user-select: text; -webkit-user-select: text;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  .expr-input:focus { border-color: var(--border-strong); box-shadow: 0 0 0 2px var(--ring); }
  .expr-input::placeholder { color: var(--subtle-foreground); }
  body.hide-raw-input .expr-input { display: none; }

  .delete-btn {
    width: 24px; height: 24px; border-radius: 7px; border: none;
    background: transparent; color: var(--subtle-foreground);
    cursor: pointer; display: grid; place-items: center; margin-top: 2px;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .delete-btn svg { width: 14px; height: 14px; }
  .delete-btn:hover { background: var(--destructive-bg); color: var(--destructive); }

  .slider-row {
    margin-top: 9px; padding-top: 9px; border-top: 1px solid var(--border);
    display: flex; align-items: center; gap: 7px;
  }
  .auto-slider-label {
    min-width: 58px; font-family: var(--font-mono); font-size: 11.5px; font-weight: 500;
    color: var(--foreground); white-space: nowrap;
  }
  .play-btn {
    width: 24px; height: 24px; border-radius: 7px; border: 1px solid var(--border);
    background: var(--glass-control); color: var(--foreground);
    cursor: pointer; display: grid; place-items: center; flex-shrink: 0;
    transition: background 0.14s ease, border-color 0.14s ease;
  }
  .play-btn:hover { background: var(--glass-control-hover); border-color: var(--border-strong); }
  .play-btn svg { width: 11px; height: 11px; }

  .bound-input {
    width: 38px; background: var(--input-bg); border: 1px solid var(--border);
    border-radius: 7px; padding: 2.5px 4px; color: var(--muted-foreground);
    font-family: var(--font-mono); font-size: 10.5px; text-align: center;
    outline: none; user-select: text; -webkit-user-select: text;
  }
  .bound-input:focus { border-color: var(--border-strong); color: var(--foreground); }

  input[type="range"].shadcn-slider {
    flex: 1; min-width: 60px; appearance: none; height: 4.5px; border-radius: 99px;
    background: var(--slider-track); outline: none; cursor: pointer;
  }
  input[type="range"].shadcn-slider::-webkit-slider-thumb {
    appearance: none; width: 14px; height: 14px; border-radius: 50%;
    background: var(--slider-thumb); border: 2px solid var(--background);
    box-shadow: 0 0 0 1px var(--border-strong), 0 2px 6px rgba(0, 0, 0, 0.45);
    cursor: pointer; transition: transform 0.12s ease;
  }
  input[type="range"].shadcn-slider::-webkit-slider-thumb:hover { transform: scale(1.12); }

  .meta-row { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .value-pill {
    margin-left: auto; font-family: var(--font-mono); font-size: 12.5px; font-weight: 500;
    padding: 3px 9px; border-radius: 8px; background: var(--input-bg);
    border: 1px solid var(--border); color: var(--foreground);
  }
  .param-pill {
    font-size: 11.5px; font-weight: 500; padding: 4px 9px; border-radius: 8px;
    border: 1px solid var(--border-strong); background: var(--glass-control);
    color: var(--foreground); cursor: pointer; display: inline-flex; align-items: center; gap: 5px;
    font-family: var(--font-sans); transition: background 0.14s ease;
  }
  .param-pill:hover { background: var(--glass-control-hover); }
  .error-pill {
    font-size: 11px; padding: 4px 8px; border-radius: 8px;
    background: var(--destructive-bg); border: 1px solid var(--destructive-border);
    color: var(--destructive); font-family: var(--font-mono); word-break: break-word;
  }

  .sidebar-toggle-float {
    position: fixed; top: 16px; left: 16px; z-index: 9;
    height: 38px; border-radius: 12px; padding: 0 14px;
    display: inline-flex; align-items: center; gap: 8px;
    color: var(--foreground); font-family: var(--font-sans); font-size: 13px; font-weight: 500;
    cursor: pointer; transition: opacity 0.2s ease, transform 0.2s ease;
  }
  .sidebar-toggle-float svg { width: 15px; height: 15px; }
  .sidebar-toggle-float.hidden { opacity: 0; pointer-events: none; transform: translateX(-10px); }

  .keypad-dock {
    position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%);
    z-index: 11; display: flex; flex-direction: column; align-items: center; gap: 8px;
    max-width: calc(100vw - 32px);
  }
  .keypad-panel {
    width: 544px; max-width: calc(100vw - 32px);
    border-radius: 18px; padding: 10px; display: flex; flex-direction: column; gap: 8px;
  }
  .keypad-panel.collapsed { display: none; }
  .keypad-tabs { display: flex; align-items: center; justify-content: center; }
  .tab-group {
    width: 100%; display: grid; grid-template-columns: repeat(3, 1fr);
    padding: 3px; border-radius: 10px; background: var(--input-bg); border: 1px solid var(--border); gap: 3px;
  }
  .tab-btn {
    height: 28px; padding: 0 11px; border-radius: 7px; border: none;
    background: transparent; color: var(--muted-foreground);
    font-family: var(--font-sans); font-size: 12px; font-weight: 500;
    cursor: pointer; transition: background 0.14s ease, color 0.14s ease;
  }
  .tab-btn:hover { color: var(--foreground); }
  .tab-btn.active { background: var(--primary); color: var(--primary-foreground); }

  .keypad-grid {
    width: 100%; height: 174px; display: grid;
    grid-template-columns: repeat(10, minmax(0, 1fr));
    grid-template-rows: repeat(4, 39px); gap: 6px;
  }
  .keypad-grid.six-col-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
    grid-template-rows: repeat(4, 39px);
  }

  .key-btn {
    width: 100%; height: 100%; border-radius: 10px; border: 1px solid var(--border);
    background: var(--glass-control); color: var(--foreground);
    font-family: var(--font-sans); font-size: 13.5px; cursor: pointer;
    display: grid; place-items: center;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
    transition: background 0.13s ease, border-color 0.13s ease, transform 0.1s ease;
  }
  .key-btn:hover { background: var(--glass-control-hover); border-color: var(--border-strong); }
  .key-btn:active { transform: scale(0.95); }
  .key-btn.key-num { background: var(--key-num); font-weight: 500; }
  .key-btn.key-num:hover { background: var(--key-num-hover); }
  .key-btn.key-op { background: var(--key-op); }
  .key-btn.key-accent { background: var(--primary); color: var(--primary-foreground); border-color: transparent; }
  .key-btn.key-accent:hover { opacity: 0.9; background: var(--primary); }
  .key-btn svg { width: 16px; height: 16px; stroke-width: 1.9; }
  .key-btn .katex { font-size: 0.96em; }

  @media (max-width: 640px) {
    .sidebar { width: 324px; }
    .keypad-panel { width: calc(100vw - 24px); }
    .keypad-grid { height: 354px; grid-template-columns: repeat(5, minmax(0, 1fr)); grid-template-rows: repeat(8, 39px); }
    .keypad-grid.six-col-grid { height: 354px; grid-template-columns: repeat(4, minmax(0, 1fr)); grid-template-rows: repeat(6, 54px); }
    .coord-hud { display: none; }
  }

  .drag-handle {
    width: 18px; height: 14px; border: none; background: transparent;
    color: var(--subtle-foreground); cursor: grab;
    display: grid; place-items: center; opacity: 0.45;
    transition: opacity 0.14s ease, color 0.14s ease;
  }
  .drag-handle:hover { opacity: 1; color: var(--foreground); }
  .drag-handle:active { cursor: grabbing; }
  .drag-handle svg { width: 13px; height: 13px; }
  .expr-card.dragging { opacity: 0.42; }
  .expr-card.drag-over-top { box-shadow: inset 0 2px 0 var(--foreground); }
  .expr-card.drag-over-bottom { box-shadow: inset 0 -2px 0 var(--foreground); }

  .card-actions {
    display: flex; flex-direction: column; align-items: center; gap: 3px;
    margin-top: 2px;
  }
  .table-toggle-btn {
    width: 24px; height: 24px; border-radius: 7px; border: none;
    background: transparent; color: var(--subtle-foreground);
    cursor: pointer; display: none; place-items: center;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .table-toggle-btn.visible { display: grid; }
  .table-toggle-btn svg { width: 13.5px; height: 13.5px; }
  .table-toggle-btn:hover { background: var(--glass-control-hover); color: var(--foreground); }
  .table-toggle-btn.active { background: var(--primary); color: var(--primary-foreground); }

  .val-table-wrap {
    margin-top: 9px; padding-top: 9px; border-top: 1px solid var(--border);
    display: flex; flex-direction: column; gap: 6px;
  }
  .val-table {
    width: 100%; border-collapse: collapse;
    font-family: var(--font-mono); font-size: 11.5px;
    border-radius: 9px; overflow: hidden;
    background: var(--input-bg); border: 1px solid var(--border);
  }
  .val-table th {
    padding: 5px 8px; text-align: left; font-weight: 500;
    color: var(--muted-foreground); border-bottom: 1px solid var(--border);
  }
  .val-table td {
    padding: 3px 6px; border-bottom: 1px solid var(--border); color: var(--foreground);
  }
  .val-table tr:last-child td { border-bottom: none; }
  .val-table-x {
    width: 100%; background: transparent; border: none; outline: none;
    color: var(--foreground); font-family: var(--font-mono); font-size: 11.5px;
    padding: 2px 3px; border-radius: 5px;
    user-select: text; -webkit-user-select: text;
  }
  .val-table-x:focus { background: var(--glass-control); }
  .val-table-y { color: var(--muted-foreground); }
  .val-table-del {
    width: 20px; height: 20px; border-radius: 5px; border: none;
    background: transparent; color: var(--subtle-foreground); cursor: pointer;
    display: grid; place-items: center;
  }
  .val-table-del:hover { color: var(--destructive); background: var(--destructive-bg); }
  .val-table-add {
    align-self: flex-start; height: 24px; padding: 0 9px;
    border-radius: 7px; border: 1px solid var(--border);
    background: var(--glass-control); color: var(--muted-foreground);
    font-family: var(--font-sans); font-size: 11px; font-weight: 500; cursor: pointer;
    transition: background 0.14s ease, color 0.14s ease;
  }
  .val-table-add:hover { background: var(--glass-control-hover); color: var(--foreground); }


  .sidebar-add-btn { padding: 0 9px; min-width: 32px; }

  .expr-card.is-folder {
    background: var(--glass-control);
    border-color: var(--border-strong);
    padding: 8px 11px;
  }
  .expr-card.in-folder {
    margin-left: 14px;
    border-left: 2px solid var(--border-strong);
  }
  .expr-card.folder-hidden { display: none; }
  .folder-row { display: flex; align-items: center; gap: 8px; }
  .folder-chevron {
    width: 24px; height: 24px; border-radius: 7px; border: none;
    background: transparent; color: var(--muted-foreground);
    cursor: pointer; display: grid; place-items: center;
    transition: transform 0.16s ease, color 0.14s ease, background 0.14s ease;
  }
  .folder-chevron:hover { background: var(--glass-control-hover); color: var(--foreground); }
  .folder-chevron.collapsed svg { transform: rotate(-90deg); }
  .folder-title-input {
    flex: 1; background: transparent; border: none; outline: none;
    color: var(--foreground); font-family: var(--font-sans);
    font-size: 13px; font-weight: 500; padding: 3px 4px;
    user-select: text; -webkit-user-select: text;
  }
  .folder-count {
    font-family: var(--font-mono); font-size: 10.5px;
    color: var(--subtle-foreground); padding: 2px 6px;
    border-radius: 6px; background: var(--input-bg); border: 1px solid var(--border);
  }
  .note-textarea {
    width: 100%; min-height: 36px; resize: vertical;
    background: transparent; border: none; outline: none;
    color: var(--muted-foreground); font-family: var(--font-sans);
    font-size: 12.5px; line-height: 1.45; padding: 2px 4px;
    user-select: text; -webkit-user-select: text;
  }
  .note-textarea::placeholder { color: var(--subtle-foreground); }

  .style-popover {
    position: fixed; z-index: 35; width: 228px;
    border-radius: 15px; padding: 11px 12px;
    display: flex; flex-direction: column; gap: 10px;
    transition: opacity 0.14s ease, transform 0.14s ease;
  }
  .style-popover.hidden { opacity: 0; pointer-events: none; transform: scale(0.96); }
  .style-swatches {
    display: grid; grid-template-columns: repeat(8, 1fr); gap: 5px;
  }
  .style-swatch {
    width: 20px; height: 20px; border-radius: 999px;
    border: 2px solid transparent; cursor: pointer;
    transition: transform 0.12s ease, border-color 0.12s ease;
  }
  .style-swatch:hover { transform: scale(1.14); }
  .style-swatch.selected { border-color: var(--foreground); box-shadow: 0 0 0 1px var(--background) inset; }
  .style-seg {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px;
    padding: 3px; border-radius: 9px; background: var(--input-bg); border: 1px solid var(--border);
  }
  .style-seg-btn {
    height: 26px; border-radius: 6px; border: none; background: transparent;
    color: var(--muted-foreground); font-size: 12px; cursor: pointer;
    display: grid; place-items: center;
  }
  .style-seg-btn.active { background: var(--primary); color: var(--primary-foreground); }
  .style-slider-row {
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    font-size: 11.5px; color: var(--muted-foreground);
  }
  .style-slider-row input[type="range"] { width: 118px; }

  .info-badge {
    font-family: var(--font-mono); font-size: 11px; font-weight: 500;
    padding: 2.5px 7px; border-radius: 7px;
    background: var(--input-bg); border: 1px solid var(--border);
    color: var(--muted-foreground);
  }
  .info-badge strong { color: var(--foreground); font-weight: 500; }

"""

SIDEBAR_HTML = r"""

  <button id="openSidebarBtn" class="liquid-glass sidebar-toggle-float hidden" title="Formelleiste öffnen">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
      <rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/>
    </svg>
    Formeln
  </button>

  <aside id="sidebar" class="liquid-glass sidebar">
    <div class="sidebar-header">
      <button id="addExprBtn" class="btn btn-primary btn-add-full" title="Neue Formel">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <path d="M5 12h14"/><path d="M12 5v14"/>
        </svg>
        Neu
      </button>
      <button id="addTableBtn" class="btn sidebar-add-btn" title="Neue Wertetabelle (für Regression y₁ ~ m x₁ + b)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M12 3v18"/>
        </svg>
      </button>
      <button id="addNoteBtn" class="btn sidebar-add-btn" title="Neue Notiz">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      </button>
      <button id="addFolderBtn" class="btn sidebar-add-btn" title="Neuer Ordner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>
        </svg>
      </button>
      <button id="collapseSidebarBtn" class="btn sidebar-add-btn" title="Seitenleiste einklappen">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <path d="m15 18-6-6 6-6"/>
        </svg>
      </button>
    </div>
    <div id="exprList" class="expr-list"></div>
  </aside>

  <div id="stylePopover" class="liquid-glass style-popover hidden">
    <div class="setting-row">
      <span class="setting-label" style="font-size:12px;">Sichtbar</span>
      <button id="stVisibleSwitch" class="switch checked" role="switch" aria-checked="true"></button>
    </div>
    <div id="stSwatches" class="style-swatches"></div>
    <div class="style-seg">
      <button class="style-seg-btn active" data-lstyle="solid" title="Durchgezogen">━━</button>
      <button class="style-seg-btn" data-lstyle="dashed" title="Gestrichelt">╌╌</button>
      <button class="style-seg-btn" data-lstyle="dotted" title="Gepunktet">···</button>
    </div>
    <div class="style-slider-row">
      <span>Stärke</span>
      <input id="stWidthSlider" type="range" class="shadcn-slider" min="1" max="6" step="0.2" value="2.4" />
    </div>
    <div class="style-slider-row">
      <span>Deckkraft</span>
      <input id="stOpacitySlider" type="range" class="shadcn-slider" min="0.15" max="1" step="0.05" value="1" />
    </div>
  </div>

  <div class="keypad-dock">
    <div id="keypadPanel" class="liquid-glass keypad-panel collapsed">
      <div class="keypad-tabs">
        <div class="tab-group">
          <button class="tab-btn active" data-tab="basic">Basis</button>
          <button class="tab-btn" data-tab="funcs">Funktionen</button>
          <button class="tab-btn" data-tab="symbols">Symbole</button>
        </div>
      </div>
      <div id="keypadGrid" class="keypad-grid"></div>
    </div>
    <button id="toggleKeypadBtn" class="liquid-glass btn" style="height: 36px; padding: 0 14px; border-radius: 12px;">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <rect width="20" height="16" x="2" y="4" rx="2"/><path d="M6 8h.001"/><path d="M10 8h.001"/><path d="M14 8h.001"/><path d="M18 8h.001"/><path d="M8 12h.001"/><path d="M12 12h.001"/><path d="M16 12h.001"/><path d="M7 16h10"/>
      </svg>
      Tastatur
    </button>
  </div>

"""

SIDEBAR_JS = r"""

  function paintSliderTrack(sliderEl, val, min, max) {
    const pct = Math.max(0, Math.min(100, ((val - min) / Math.max(max - min, 1e-9)) * 100));
    sliderEl.style.background =
      `linear-gradient(to right, var(--slider-fill) 0%, var(--slider-fill) ${pct}%, var(--slider-track) ${pct}%, var(--slider-track) 100%)`;
  }

  const ICON_PLAY = `<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>`;
  const ICON_PAUSE = `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>`;
  const ICON_X = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`;
  const ICON_BACKSPACE = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M21 4H8l-7 8 7 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z"/><line x1="18" y1="9" x2="12" y2="15"/><line x1="12" y1="9" x2="18" y2="15"/></svg>`;
  const ICON_ENTER = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 10 4 15 9 20"/><path d="M20 4v7a4 4 0 0 1-4 4H4"/></svg>`;
  const ICON_GRIP = `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/></svg>`;
  const ICON_TABLE = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M12 3v18"/></svg>`;
  const ICON_CHEVRON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`;

  let draggedExprId = null;
  let styleTargetId = null;

  const stylePopover = document.getElementById("stylePopover");
  const stVisibleSwitch = document.getElementById("stVisibleSwitch");
  const stSwatches = document.getElementById("stSwatches");
  const stWidthSlider = document.getElementById("stWidthSlider");
  const stOpacitySlider = document.getElementById("stOpacitySlider");

  function closeStylePopover() {
    stylePopover.classList.add("hidden");
    styleTargetId = null;
  }

  function openStylePopover(ex, anchorEl) {
    if (styleTargetId === ex.id && !stylePopover.classList.contains("hidden")) {
      closeStylePopover();
      return;
    }
    styleTargetId = ex.id;
    const rect = anchorEl.getBoundingClientRect();
    let left = rect.right + 10;
    let top = rect.top - 10;
    if (left + 236 > window.innerWidth) left = rect.left - 240;
    if (top + 200 > window.innerHeight) top = window.innerHeight - 210;
    if (top < 12) top = 12;
    stylePopover.style.left = left + "px";
    stylePopover.style.top = top + "px";

    stVisibleSwitch.classList.toggle("checked", Boolean(ex.visible));
    stVisibleSwitch.setAttribute("aria-checked", String(Boolean(ex.visible)));

    const pal = isLight() ? PALETTE_LIGHT : PALETTE_DARK;
    stSwatches.innerHTML = "";
    pal.forEach((hex, idx) => {
      const sw = document.createElement("button");
      sw.className = "style-swatch" + (ex.colorIdx === idx ? " selected" : "");
      sw.style.background = hex;
      sw.addEventListener("click", () => {
        ex.colorIdx = idx;
        stSwatches.querySelectorAll(".style-swatch").forEach((b, i) => b.classList.toggle("selected", i === idx));
        syncExprCards();
        drawScene();
        pushHistory();
      });
      stSwatches.append(sw);
    });

    const curStyle = ex.lineStyle || "solid";
    stylePopover.querySelectorAll(".style-seg-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.lstyle === curStyle);
    });

    const lw = ex.lineWidth ?? 2.4;
    stWidthSlider.value = lw;
    paintSliderTrack(stWidthSlider, lw, 1, 6);

    const op = ex.opacity ?? 1.0;
    stOpacitySlider.value = op;
    paintSliderTrack(stOpacitySlider, op, 0.15, 1);

    stylePopover.classList.remove("hidden");
  }

  stVisibleSwitch.addEventListener("click", () => {
    const ex = expressions.find((e) => e.id === styleTargetId);
    if (!ex) return;
    ex.visible = !ex.visible;
    stVisibleSwitch.classList.toggle("checked", ex.visible);
    syncExprCards();
    drawScene();
    scheduleCompute(20);
    pushHistory();
  });

  stylePopover.querySelectorAll(".style-seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ex = expressions.find((e) => e.id === styleTargetId);
      if (!ex) return;
      ex.lineStyle = btn.dataset.lstyle;
      stylePopover.querySelectorAll(".style-seg-btn").forEach((b) => b.classList.toggle("active", b === btn));
      drawScene();
      pushHistory();
    });
  });

  stWidthSlider.addEventListener("input", () => {
    const ex = expressions.find((e) => e.id === styleTargetId);
    if (!ex) return;
    ex.lineWidth = parseFloat(stWidthSlider.value);
    paintSliderTrack(stWidthSlider, ex.lineWidth, 1, 6);
    drawScene();
  });
  stWidthSlider.addEventListener("change", () => pushHistory());

  stOpacitySlider.addEventListener("input", () => {
    const ex = expressions.find((e) => e.id === styleTargetId);
    if (!ex) return;
    ex.opacity = parseFloat(stOpacitySlider.value);
    paintSliderTrack(stOpacitySlider, ex.opacity, 0.15, 1);
    drawScene();
  });
  stOpacitySlider.addEventListener("change", () => pushHistory());

  document.addEventListener("mousedown", (e) => {
    if (!stylePopover.classList.contains("hidden") && !stylePopover.contains(e.target) && !e.target.closest(".color-dot")) {
      closeStylePopover();
    }
  });

  function formatNumber(v) {
    if (Math.abs(v) < 1e-12) return "0";
    if (Math.abs(v) >= 1e7 || (Math.abs(v) > 0 && Math.abs(v) < 1e-5)) return v.toExponential(5);
    return String(Number(v.toPrecision(10)));
  }

  function formatVarLatex(name) {
    const greek = {
      sigma: "\\sigma", mu: "\\mu", alpha: "\\alpha", beta: "\\beta",
      phi: "\\phi", omega: "\\omega", Delta: "\\Delta",
    };
    return greek[name] || name;
  }

  function setActiveExpr(id) {
    if (activeExprId === id) return;
    activeExprId = id;
    exprListEl.querySelectorAll(".expr-card").forEach((c) => {
      c.classList.toggle("focused", Number(c.dataset.cardId) === activeExprId);
    });
    drawScene();
  }

  function configureMathField(mf, ex) {
    if (!mf) return;
    try { mf.setAttribute("math-virtual-keyboard-policy", "manual"); } catch (_) {}
    try { mf.mathVirtualKeyboardPolicy = "manual"; } catch (_) {}
    try { mf.menuItems = []; } catch (_) {}
    try { mf.smartFence = true; } catch (_) {}
    try { mf.smartSuperscript = true; } catch (_) {}
    try {
      if (mf.inlineShortcuts && typeof mf.inlineShortcuts === "object") {
        mf.inlineShortcuts = {
          ...mf.inlineShortcuts,
          sum: String.raw`\sum\limits_{n=#?}^{#?}#?`,
          prod: String.raw`\prod\limits_{n=#?}^{#?}#?`,
          int: String.raw`\int_{#?}^{#?}#?\,dx`,
        };
      }
    } catch (_) {}
    try { if (ex.raw && mf.value !== ex.raw) mf.value = ex.raw; } catch (_) {}
  }

  function syncPlaceholderAndFallback(card, ex) {
    const wrap = card.querySelector(".math-editor-wrap");
    if (wrap) wrap.classList.toggle("has-value", Boolean(ex.raw && ex.raw.trim()));
    const fb = card.querySelector(".latex-fallback");
    if (fb && !window.__mathLiveLoaded) renderLatex(fb, ex.result?.latex || ex.raw || "");
  }

  function attachCardDragEvents(card, ex) {
    card.addEventListener("dragstart", (ev) => {
      draggedExprId = ex.id;
      card.classList.add("dragging");
      ev.dataTransfer.effectAllowed = "move";
      try { ev.dataTransfer.setData("text/plain", String(ex.id)); } catch (_) {}
    });
    card.addEventListener("dragend", () => {
      draggedExprId = null;
      card.draggable = false;
      card.classList.remove("dragging");
      exprListEl.querySelectorAll(".expr-card").forEach((c) => {
        c.classList.remove("drag-over-top", "drag-over-bottom");
      });
    });
    card.addEventListener("dragover", (ev) => {
      if (draggedExprId === null || draggedExprId === ex.id) return;
      ev.preventDefault();
      ev.dataTransfer.dropEffect = "move";
      const rect = card.getBoundingClientRect();
      const above = ev.clientY < rect.top + rect.height / 2;
      card.classList.toggle("drag-over-top", above);
      card.classList.toggle("drag-over-bottom", !above);
    });
    card.addEventListener("dragleave", () => {
      card.classList.remove("drag-over-top", "drag-over-bottom");
    });
    card.addEventListener("drop", (ev) => {
      ev.preventDefault();
      if (draggedExprId === null || draggedExprId === ex.id) return;
      const rect = card.getBoundingClientRect();
      const insertBefore = ev.clientY < rect.top + rect.height / 2;
      const fromIdx = expressions.findIndex((e) => e.id === draggedExprId);
      if (fromIdx < 0) return;
      const [moved] = expressions.splice(fromIdx, 1);

      let movedBlock = [moved];
      if (moved.type === "folder") {
        if (ex.folderId === moved.id) {
          expressions.splice(fromIdx, 0, moved);
          return;
        }
        const children = expressions.filter((e) => e.folderId === moved.id);
        expressions = expressions.filter((e) => e.folderId !== moved.id);
        movedBlock = [moved, ...children];
      }

      let toIdx = expressions.findIndex((e) => e.id === ex.id);
      if (toIdx < 0) toIdx = expressions.length;

      if (ex.type === "folder" && moved.type !== "folder" && !insertBefore) {
        moved.folderId = ex.id;
        toIdx += 1;
      } else if (moved.type !== "folder") {
        moved.folderId = ex.folderId || null;
        if (!insertBefore) toIdx += 1;
      } else {
        if (!insertBefore) {
          toIdx += 1;
          if (ex.type === "folder") {
            while (toIdx < expressions.length && expressions[toIdx].folderId === ex.id) toIdx++;
          }
        }
      }

      expressions.splice(toIdx, 0, ...movedBlock);
      card.classList.remove("drag-over-top", "drag-over-bottom");
      syncExprCards();
      drawScene();
      scheduleCompute(15);
      pushHistory();
    });
  }

  function removeExpressionById(id) {
    const target = expressions.find((e) => e.id === id);
    if (target && target.type === "folder") {
      expressions.forEach((e) => { if (e.folderId === id) e.folderId = null; });
    }
    expressions = expressions.filter((e) => e.id !== id);
    if (expressions.length === 0) addExpression("");
    else {
      if (activeExprId === id) activeExprId = expressions[expressions.length - 1].id;
      syncExprCards();
      scheduleCompute(10);
      pushHistory();
    }
  }

  function createExprCard(ex) {
    const card = document.createElement("div");
    card.className = "expr-card" + (ex.id === activeExprId ? " focused" : "");
    card.dataset.cardId = ex.id;
    card.dataset.cardType = ex.type || "expr";
    card.dataset.extrasSig = "";
    card.draggable = false;
    attachCardDragEvents(card, ex);

    const makeGrip = () => {
      const g = document.createElement("button");
      g.className = "drag-handle";
      g.innerHTML = ICON_GRIP;
      g.title = "Ziehen zum Sortieren";
      g.addEventListener("mousedown", () => { card.draggable = true; });
      g.addEventListener("mouseup", () => { card.draggable = false; });
      return g;
    };

    const makeDeleteBtn = () => {
      const del = document.createElement("button");
      del.className = "delete-btn";
      del.innerHTML = ICON_X;
      del.title = "Entfernen";
      del.addEventListener("click", (ev) => {
        ev.stopPropagation();
        removeExpressionById(ex.id);
      });
      return del;
    };

    if (ex.type === "folder") {
      card.classList.add("is-folder");
      const row = document.createElement("div");
      row.className = "folder-row";

      const chev = document.createElement("button");
      chev.className = "folder-chevron" + (ex.collapsed ? " collapsed" : "");
      chev.innerHTML = ICON_CHEVRON;
      chev.title = "Ordner ein-/ausklappen";
      chev.addEventListener("click", (ev) => {
        ev.stopPropagation();
        ex.collapsed = !ex.collapsed;
        chev.classList.toggle("collapsed", ex.collapsed);
        syncExprCards();
        pushHistory();
      });

      const titleIn = document.createElement("input");
      titleIn.className = "folder-title-input";
      titleIn.value = ex.title || "Ordner";
      titleIn.placeholder = "Ordnername…";
      titleIn.addEventListener("input", () => { ex.title = titleIn.value; scheduleHistoryPush(); });

      const cnt = document.createElement("span");
      cnt.className = "folder-count";
      cnt.textContent = "0";

      row.append(makeGrip(), chev, titleIn, cnt, makeDeleteBtn());
      card.append(row);
      return card;
    }

    if (ex.type === "note") {
      const top = document.createElement("div");
      top.className = "expr-top";
      const gutter = document.createElement("div");
      gutter.className = "expr-gutter";
      const num = document.createElement("span");
      num.className = "expr-num";
      gutter.append(makeGrip(), num);

      const ta = document.createElement("textarea");
      ta.className = "note-textarea";
      ta.rows = 2;
      ta.value = ex.text || "";
      ta.placeholder = "Notiz oder Kommentar eingeben…";
      ta.addEventListener("input", () => { ex.text = ta.value; scheduleHistoryPush(); });

      top.append(gutter, ta, makeDeleteBtn());
      card.append(top);
      return card;
    }

    if (ex.type === "table") {
      const top = document.createElement("div");
      top.className = "expr-top";
      const gutter = document.createElement("div");
      gutter.className = "expr-gutter";
      const num = document.createElement("span");
      num.className = "expr-num";
      const dot = document.createElement("button");
      dot.className = "color-dot";
      dot.title = "Stil & Farbe";
      dot.addEventListener("click", (ev) => { ev.stopPropagation(); openStylePopover(ex, dot); });
      gutter.append(makeGrip(), num, dot);

      const body = document.createElement("div");
      body.className = "expr-body";
      const extras = document.createElement("div");
      extras.className = "card-extras";
      body.append(extras);

      top.append(gutter, body, makeDeleteBtn());
      card.append(top);
      return card;
    }

    const top = document.createElement("div");
    top.className = "expr-top";

    const gutter = document.createElement("div");
    gutter.className = "expr-gutter";

    const num = document.createElement("span");
    num.className = "expr-num";

    const dot = document.createElement("button");
    dot.className = "color-dot";
    dot.title = "Farbe, Linienstil & Sichtbarkeit";
    dot.addEventListener("click", (ev) => {
      ev.stopPropagation();
      openStylePopover(ex, dot);
    });
    dot.addEventListener("contextmenu", (ev) => {
      ev.preventDefault();
      ex.visible = !ex.visible;
      dot.classList.toggle("hidden-curve", !ex.visible);
      drawScene();
      scheduleCompute(20);
      pushHistory();
    });
    gutter.append(makeGrip(), num, dot);

    const body = document.createElement("div");
    body.className = "expr-body";

    const wrap = document.createElement("div");
    wrap.className = "math-editor-wrap" + ((ex.raw || "").trim() ? " has-value" : "");

    const placeholder = document.createElement("span");
    placeholder.className = "math-placeholder";
    placeholder.textContent = "Ausdruck eingeben…";

    const mf = document.createElement("math-field");
    mf.className = "math-editor";
    mf.dataset.mfId = ex.id;
    mf.setAttribute("math-virtual-keyboard-policy", "manual");

    const fallback = document.createElement("div");
    fallback.className = "latex-fallback";

    wrap.append(placeholder, mf, fallback);

    const input = document.createElement("input");
    input.type = "text";
    input.className = "expr-input";
    input.dataset.inputId = ex.id;
    input.value = ex.raw || "";
    input.placeholder = String.raw`y = \sin(x), z = \sin(\sqrt{x^2+y^2}), y' = x-y`;

    mf.addEventListener("focus", () => setActiveExpr(ex.id));
    mf.addEventListener("input", () => {
      try { ex.raw = mf.value || ""; } catch (_) {}
      if (document.activeElement !== input) input.value = ex.raw;
      syncPlaceholderAndFallback(card, ex);
      scheduleCompute(95);
      scheduleHistoryPush();
    });
    mf.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        ev.stopPropagation();
        addExpression("");
      }
    }, true);

    input.addEventListener("focus", () => setActiveExpr(ex.id));
    input.addEventListener("input", () => {
      ex.raw = input.value;
      if (document.activeElement !== mf && window.__mathLiveLoaded) {
        try { mf.value = ex.raw; } catch (_) {}
      }
      syncPlaceholderAndFallback(card, ex);
      scheduleCompute(95);
      scheduleHistoryPush();
    });
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") { ev.preventDefault(); addExpression(""); }
    });

    card.addEventListener("mousedown", (ev) => {
      setActiveExpr(ex.id);
      if (ev.target === card || ev.target === top || ev.target === body || ev.target === wrap) {
        if (window.__mathLiveLoaded) mf.focus();
        else if (settings.showRawInput) input.focus();
      }
    });

    body.append(wrap, input);

    const actions = document.createElement("div");
    actions.className = "card-actions";

    const tblBtn = document.createElement("button");
    tblBtn.className = "table-toggle-btn";
    tblBtn.innerHTML = ICON_TABLE;
    tblBtn.title = "Wertetabelle ein-/ausblenden";
    tblBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      ex.showTable = !ex.showTable;
      if (!ex.tableXs) ex.tableXs = [-2, -1, 0, 1, 2];
      tblBtn.classList.toggle("active", ex.showTable);
      card.dataset.extrasSig = "";
      syncExprCards();
      scheduleCompute(10);
      pushHistory();
    });

    actions.append(makeDeleteBtn(), tblBtn);
    top.append(gutter, body, actions);

    const extras = document.createElement("div");
    extras.className = "card-extras";

    card.append(top, extras);
    return card;
  }

  function renderStandaloneTable(card, ex) {
    const tblIdx = ex.result?.table_index || 1;
    const rows = ex.rows || [[0, 0], [1, 1], [2, 2]];
    const sig = JSON.stringify({ t: "standalone_table", idx: tblIdx, len: rows.length });
    if (card.dataset.extrasSig === sig) return;
    card.dataset.extrasSig = sig;

    const extras = card.querySelector(".card-extras");
    extras.innerHTML = "";

    const tWrap = document.createElement("div");
    tWrap.className = "val-table-wrap";
    tWrap.style.marginTop = "0";
    tWrap.style.paddingTop = "0";
    tWrap.style.borderTop = "none";

    const tbl = document.createElement("table");
    tbl.className = "val-table";
    tbl.innerHTML = `<thead><tr><th style="width:45%">x<sub>${tblIdx}</sub></th><th style="width:45%">y<sub>${tblIdx}</sub></th><th style="width:10%"></th></tr></thead>`;
    const tbody = document.createElement("tbody");

    const handleCsvPaste = (ev) => {
      const clip = ev.clipboardData?.getData("text") || "";
      if (!clip.includes("\n") && !clip.includes(",") && !clip.includes("\t")) return;
      const lines = clip.trim().split(/\r?\n/);
      const parsedRows = [];
      for (const line of lines) {
        const parts = line.trim().split(/[\t,;]+/).map((p) => parseFloat(p.trim()));
        if (parts.length >= 2 && !Number.isNaN(parts[0]) && !Number.isNaN(parts[1])) {
          parsedRows.push([parts[0], parts[1]]);
        }
      }
      if (parsedRows.length >= 2) {
        ev.preventDefault();
        ex.rows = parsedRows;
        card.dataset.extrasSig = "";
        syncExprCards();
        scheduleCompute(15);
        pushHistory();
      }
    };

    rows.forEach((row, rIdx) => {
      const tr = document.createElement("tr");

      const tdX = document.createElement("td");
      const xIn = document.createElement("input");
      xIn.className = "val-table-x";
      xIn.value = row[0] ?? "";
      xIn.addEventListener("paste", handleCsvPaste);
      xIn.addEventListener("input", () => {
        const v = parseFloat(xIn.value.replace(",", "."));
        ex.rows[rIdx][0] = Number.isNaN(v) ? "" : v;
        scheduleCompute(60);
        scheduleHistoryPush();
      });
      tdX.append(xIn);

      const tdY = document.createElement("td");
      const yIn = document.createElement("input");
      yIn.className = "val-table-x";
      yIn.value = row[1] ?? "";
      yIn.addEventListener("paste", handleCsvPaste);
      yIn.addEventListener("input", () => {
        const v = parseFloat(yIn.value.replace(",", "."));
        ex.rows[rIdx][1] = Number.isNaN(v) ? "" : v;
        scheduleCompute(60);
        scheduleHistoryPush();
      });
      tdY.append(yIn);

      const tdDel = document.createElement("td");
      const rDel = document.createElement("button");
      rDel.className = "val-table-del";
      rDel.innerHTML = ICON_X;
      rDel.addEventListener("click", () => {
        ex.rows.splice(rIdx, 1);
        card.dataset.extrasSig = "";
        syncExprCards();
        scheduleCompute(15);
        pushHistory();
      });
      tdDel.append(rDel);

      tr.append(tdX, tdY, tdDel);
      tbody.append(tr);
    });

    tbl.append(tbody);

    const footer = document.createElement("div");
    footer.style.display = "flex";
    footer.style.alignItems = "center";
    footer.style.justifyContent = "space-between";
    footer.style.gap = "6px";

    const addRowBtn = document.createElement("button");
    addRowBtn.className = "val-table-add";
    addRowBtn.textContent = "+ Punkt";
    addRowBtn.addEventListener("click", () => {
      const lastX = ex.rows.length ? Number(ex.rows[ex.rows.length - 1][0]) : -1;
      ex.rows.push([Number.isFinite(lastX) ? lastX + 1 : 0, 0]);
      card.dataset.extrasSig = "";
      syncExprCards();
      scheduleCompute(15);
      pushHistory();
    });

    const hint = document.createElement("span");
    hint.className = "info-badge";
    hint.textContent = `y_${tblIdx} ~ m x_${tblIdx} + b`;

    footer.append(addRowBtn, hint);
    tWrap.append(tbl, footer);
    extras.append(tWrap);
  }

  function updateCardExtras(card, ex, renderedAutoVars) {
    if (ex.type === "note" || ex.type === "folder") return;
    if (ex.type === "table") {
      renderStandaloneTable(card, ex);
      return;
    }

    const res = ex.result;
    const tblBtn = card.querySelector(".table-toggle-btn");
    if (tblBtn) {
      const canTable = Boolean(res?.supports_table);
      tblBtn.classList.toggle("visible", canTable);
      tblBtn.classList.toggle("active", Boolean(canTable && ex.showTable));
    }

    const myAutoVars = [];
    if (settings.autoSliders && res && Array.isArray(res.auto_vars)) {
      for (const vname of res.auto_vars) {
        if (!renderedAutoVars.has(vname) && autoSliders[vname]) {
          renderedAutoVars.add(vname);
          myAutoVars.push(vname);
        }
      }
    }

    const tableVisible = Boolean(ex.showTable && res?.supports_table);
    const sig = JSON.stringify({
      k: res?.kind || "",
      sn: res?.kind === "slider" ? res.name : "",
      av: myAutoVars,
      ms: res?.missing || [],
      err: res?.error || "",
      cnt: res?.count ?? null,
      regKeys: res?.kind === "regression" && res?.params ? Object.keys(res.params) : null,
      m3d: (res?.kind === "surface3d" || res?.kind === "parametric_surface3d" || res?.kind === "curve3d" || res?.kind === "point3d" || res?.kind === "implicit3d") ? mode3D : null,
      tblOn: tableVisible,
      tblLen: tableVisible ? (ex.tableXs?.length || 0) : 0,
    });

    if (card.dataset.extrasSig === sig) {
      const vp = card.querySelector(".value-pill");
      if (res?.kind === "value" || res?.kind === "integral_area") {
        if (vp) vp.textContent = "= " + formatNumber(res.value);
      } else if (res?.kind === "point" && Array.isArray(res.point)) {
        if (vp) vp.textContent = `(${formatNumber(res.point[0])}, ${formatNumber(res.point[1])})`;
      } else if (res?.kind === "point3d" && Array.isArray(res.point)) {
        if (vp) vp.textContent = `(${formatNumber(res.point[0])}, ${formatNumber(res.point[1])}, ${formatNumber(res.point[2])})`;
      } else if (res?.kind === "slider") {
        const rng = card.querySelector(`input[data-explicit-range="${ex.id}"]`);
        if (rng && document.activeElement !== rng) {
          if (res.value < ex.min) {
            ex.min = Math.floor(res.value - 2);
            rng.min = ex.min;
            const bIns = card.querySelectorAll(".bound-input");
            if (bIns[0]) bIns[0].value = ex.min;
          }
          if (res.value > ex.max) {
            ex.max = Math.ceil(res.value + 2);
            rng.max = ex.max;
            const bIns = card.querySelectorAll(".bound-input");
            if (bIns[1]) bIns[1].value = ex.max;
          }
          rng.value = res.value;
          paintSliderTrack(rng, res.value, ex.min, ex.max);
        }
      } else if (res?.kind === "regression" && res.params) {
        const badges = card.querySelectorAll(".info-badge");
        const entries = Object.entries(res.params);
        entries.forEach(([k, v], i) => {
          if (badges[i]) badges[i].innerHTML = `${k} = <strong>${formatNumber(v)}</strong>`;
        });
        if (badges[entries.length]) badges[entries.length].innerHTML = `R² = <strong>${res.r2}</strong>`;
      }
      if (tableVisible && Array.isArray(res?.table)) {
        const yCells = card.querySelectorAll(".val-table-y");
        res.table.forEach((row, idx) => {
          if (yCells[idx]) yCells[idx].textContent = row[1] === null ? "undef" : formatNumber(row[1]);
        });
      }
      return;
    }
    card.dataset.extrasSig = sig;

    const extras = card.querySelector(".card-extras");
    extras.innerHTML = "";
    if (!res) return;

    const mf = card.querySelector("math-field");
    const input = card.querySelector(".expr-input");

    if (res.kind === "value" || res.kind === "integral_area") {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      if (res.kind === "integral_area") {
        const badge = document.createElement("span");
        badge.className = "info-badge";
        badge.textContent = "Fläche";
        meta.append(badge);
      }
      const valPill = document.createElement("div");
      valPill.className = "value-pill";
      valPill.textContent = "= " + formatNumber(res.value);
      meta.append(valPill);
      extras.append(meta);
    }

    if (res.kind === "list") {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      const badge = document.createElement("span");
      badge.className = "info-badge";
      badge.innerHTML = `Liste · <strong>${res.count} Werte</strong>`;
      meta.append(badge);
      extras.append(meta);
    }

    if (res.kind === "curve_family") {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      const badge = document.createElement("span");
      badge.className = "info-badge";
      badge.innerHTML = `Kurvenschar · <strong>${res.count} Graphen</strong>`;
      meta.append(badge);
      extras.append(meta);
    }

    if (res.kind === "slope_field") {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      const badge = document.createElement("span");
      badge.className = "info-badge";
      badge.textContent = "Richtungsfeld";
      meta.append(badge);
      extras.append(meta);
    }

    if ((res.kind === "surface3d" || res.kind === "parametric_surface3d" || res.kind === "curve3d" || res.kind === "point3d" || res.kind === "implicit3d") && !mode3D) {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      const btn3d = document.createElement("button");
      btn3d.className = "param-pill";
      btn3d.textContent = "In 3D anzeigen";
      btn3d.addEventListener("click", () => setMode3D(true));
      meta.append(btn3d);
      extras.append(meta);
    }

    if (res.kind === "point3d" && Array.isArray(res.point)) {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      const valPill = document.createElement("div");
      valPill.className = "value-pill";
      valPill.textContent = `(${formatNumber(res.point[0])}, ${formatNumber(res.point[1])}, ${formatNumber(res.point[2])})`;
      meta.append(valPill);
      extras.append(meta);
    }

    if (res.kind === "regression" && res.params) {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      for (const [k, v] of Object.entries(res.params)) {
        const b = document.createElement("span");
        b.className = "info-badge";
        b.innerHTML = `${k} = <strong>${formatNumber(v)}</strong>`;
        meta.append(b);
      }
      const r2b = document.createElement("span");
      r2b.className = "info-badge";
      r2b.innerHTML = `R² = <strong>${res.r2}</strong>`;
      meta.append(r2b);
      extras.append(meta);
    }

    if (res.kind === "point" && Array.isArray(res.point)) {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      const valPill = document.createElement("div");
      valPill.className = "value-pill";
      valPill.textContent = `(${formatNumber(res.point[0])}, ${formatNumber(res.point[1])})`;
      meta.append(valPill);
      extras.append(meta);
    }

    if (res.kind === "slider") {
      const sRow = document.createElement("div");
      sRow.className = "slider-row";

      const playBtn = document.createElement("button");
      playBtn.className = "play-btn";
      playBtn.innerHTML = ex.playing ? ICON_PAUSE : ICON_PLAY;
      playBtn.title = "Parameter animieren";
      playBtn.addEventListener("click", () => {
        ex.playing = !ex.playing;
        playBtn.innerHTML = ex.playing ? ICON_PAUSE : ICON_PLAY;
      });

      const minIn = document.createElement("input");
      minIn.className = "bound-input";
      minIn.value = ex.min;

      const slider = document.createElement("input");
      slider.type = "range";
      slider.className = "shadcn-slider";
      slider.dataset.explicitRange = ex.id;
      slider.min = ex.min;
      slider.max = ex.max;
      slider.step = ex.step || 0.05;
      slider.value = res.value;
      paintSliderTrack(slider, res.value, ex.min, ex.max);

      const maxIn = document.createElement("input");
      maxIn.className = "bound-input";
      maxIn.value = ex.max;

      minIn.addEventListener("change", () => {
        const v = parseFloat(minIn.value);
        if (!Number.isNaN(v)) { ex.min = v; slider.min = v; paintSliderTrack(slider, res.value, ex.min, ex.max); pushHistory(); }
      });
      maxIn.addEventListener("change", () => {
        const v = parseFloat(maxIn.value);
        if (!Number.isNaN(v)) { ex.max = v; slider.max = v; paintSliderTrack(slider, res.value, ex.min, ex.max); pushHistory(); }
      });
      slider.addEventListener("input", () => {
        const val = parseFloat(slider.value);
        ex.result.value = val;
        const formatted = val.toFixed(2).replace(/\.?0+$/, "");
        ex.raw = `${formatVarLatex(ex.result.name)} = ${formatted}`;
        if (mf && window.__mathLiveLoaded) { try { mf.value = ex.raw; } catch (_) {} }
        if (input) input.value = ex.raw;
        syncPlaceholderAndFallback(card, ex);
        paintSliderTrack(slider, val, ex.min, ex.max);
        requestComputeLive();
      });
      slider.addEventListener("change", () => pushHistory());

      sRow.append(playBtn, minIn, slider, maxIn);
      extras.append(sRow);
    }

    for (const vname of myAutoVars) {
      const st = autoSliders[vname];
      const aRow = document.createElement("div");
      aRow.className = "slider-row";
      aRow.dataset.autoSlider = vname;

      const playBtn = document.createElement("button");
      playBtn.className = "play-btn";
      playBtn.innerHTML = st.playing ? ICON_PAUSE : ICON_PLAY;
      playBtn.title = `${vname} animieren`;
      playBtn.addEventListener("click", () => {
        st.playing = !st.playing;
        playBtn.innerHTML = st.playing ? ICON_PAUSE : ICON_PLAY;
      });

      const lbl = document.createElement("span");
      lbl.className = "auto-slider-label";
      lbl.dataset.autoLabel = vname;
      renderLatex(lbl, `${formatVarLatex(vname)} = ${st.value.toFixed(2)}`);

      const minIn = document.createElement("input");
      minIn.className = "bound-input";
      minIn.value = st.min;

      const slider = document.createElement("input");
      slider.type = "range";
      slider.className = "shadcn-slider";
      slider.dataset.autoRange = vname;
      slider.min = st.min;
      slider.max = st.max;
      slider.step = st.step;
      slider.value = st.value;
      paintSliderTrack(slider, st.value, st.min, st.max);

      const maxIn = document.createElement("input");
      maxIn.className = "bound-input";
      maxIn.value = st.max;

      minIn.addEventListener("change", () => {
        const v = parseFloat(minIn.value);
        if (!Number.isNaN(v)) { st.min = v; slider.min = v; paintSliderTrack(slider, st.value, st.min, st.max); pushHistory(); }
      });
      maxIn.addEventListener("change", () => {
        const v = parseFloat(maxIn.value);
        if (!Number.isNaN(v)) { st.max = v; slider.max = v; paintSliderTrack(slider, st.value, st.min, st.max); pushHistory(); }
      });
      slider.addEventListener("input", () => {
        const val = parseFloat(slider.value);
        st.value = val;
        paintSliderTrack(slider, val, st.min, st.max);
        renderLatex(lbl, `${formatVarLatex(vname)} = ${val.toFixed(2)}`);
        requestComputeLive();
      });
      slider.addEventListener("change", () => pushHistory());

      aRow.append(playBtn, lbl, minIn, slider, maxIn);
      extras.append(aRow);
    }

    if (tableVisible) {
      if (!ex.tableXs) ex.tableXs = [-2, -1, 0, 1, 2];
      const tWrap = document.createElement("div");
      tWrap.className = "val-table-wrap";

      const tbl = document.createElement("table");
      tbl.className = "val-table";
      tbl.innerHTML = `<thead><tr><th style="width:44%">x</th><th style="width:46%">y</th><th style="width:10%"></th></tr></thead>`;
      const tbody = document.createElement("tbody");

      ex.tableXs.forEach((xv, rIdx) => {
        const tr = document.createElement("tr");
        const tdX = document.createElement("td");
        const xIn = document.createElement("input");
        xIn.className = "val-table-x";
        xIn.value = String(xv);
        xIn.addEventListener("input", () => {
          const parsed = parseFloat(xIn.value.replace(",", "."));
          if (!Number.isNaN(parsed)) {
            ex.tableXs[rIdx] = parsed;
            scheduleCompute(60);
            scheduleHistoryPush();
          }
        });
        tdX.append(xIn);

        const tdY = document.createElement("td");
        tdY.className = "val-table-y";
        const yVal = res.table && res.table[rIdx] ? res.table[rIdx][1] : null;
        tdY.textContent = yVal === null || yVal === undefined ? "…" : formatNumber(yVal);

        const tdDel = document.createElement("td");
        const rDel = document.createElement("button");
        rDel.className = "val-table-del";
        rDel.innerHTML = ICON_X;
        rDel.title = "Zeile löschen";
        rDel.addEventListener("click", () => {
          ex.tableXs.splice(rIdx, 1);
          card.dataset.extrasSig = "";
          syncExprCards();
          scheduleCompute(15);
          pushHistory();
        });
        tdDel.append(rDel);

        tr.append(tdX, tdY, tdDel);
        tbody.append(tr);
      });

      tbl.append(tbody);

      const addRowBtn = document.createElement("button");
      addRowBtn.className = "val-table-add";
      addRowBtn.textContent = "+ Zeile";
      addRowBtn.addEventListener("click", () => {
        const last = ex.tableXs.length ? ex.tableXs[ex.tableXs.length - 1] : 0;
        const step = ex.tableXs.length >= 2 ? (ex.tableXs[ex.tableXs.length - 1] - ex.tableXs[ex.tableXs.length - 2]) : 1;
        ex.tableXs.push(Number((last + (step || 1)).toPrecision(6)));
        card.dataset.extrasSig = "";
        syncExprCards();
        scheduleCompute(15);
        pushHistory();
      });

      tWrap.append(tbl, addRowBtn);
      extras.append(tWrap);
    }

    if (res.kind === "needs_params" && res.missing?.length) {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      res.missing.forEach((pName) => {
        const pill = document.createElement("button");
        pill.className = "param-pill";
        pill.textContent = `+ Slider ${pName}`;
        pill.addEventListener("click", () => addExpression(`${pName} = 1`, false));
        meta.append(pill);
      });
      extras.append(meta);
    }

    if (res.kind === "error") {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      const errPill = document.createElement("div");
      errPill.className = "error-pill";
      errPill.textContent = res.error;
      meta.append(errPill);
      extras.append(meta);
    }
  }

  function syncExprCards() {
    const validIds = new Set(expressions.map((e) => String(e.id)));
    Array.from(exprListEl.children).forEach((child) => {
      if (!validIds.has(child.dataset.cardId)) child.remove();
    });

    const folderCollapsed = {};
    const folderCounts = {};
    for (const ex of expressions) {
      if (ex.type === "folder") {
        folderCollapsed[ex.id] = Boolean(ex.collapsed);
        folderCounts[ex.id] = 0;
      }
    }
    for (const ex of expressions) {
      if (ex.folderId && folderCounts[ex.folderId] !== undefined) {
        folderCounts[ex.folderId]++;
      }
    }

    const renderedAutoVars = new Set();

    expressions.forEach((ex, index) => {
      let card = exprListEl.querySelector(`.expr-card[data-card-id="${ex.id}"]`);
      let isNew = false;
      if (!card || card.dataset.cardType !== (ex.type || "expr")) {
        if (card) card.remove();
        card = createExprCard(ex);
        exprListEl.append(card);
        isNew = true;
      }

      if (exprListEl.children[index] !== card) {
        exprListEl.insertBefore(card, exprListEl.children[index] || null);
      }

      if (isNew && (ex.type || "expr") === "expr" && window.__mathLiveLoaded) {
        configureMathField(card.querySelector("math-field"), ex);
      }

      card.classList.toggle("focused", ex.id === activeExprId);
      const inFolder = Boolean(ex.folderId && folderCollapsed[ex.folderId] !== undefined);
      card.classList.toggle("in-folder", inFolder);
      card.classList.toggle("folder-hidden", inFolder && Boolean(folderCollapsed[ex.folderId]));

      if (ex.type === "folder") {
        const cntEl = card.querySelector(".folder-count");
        if (cntEl) cntEl.textContent = String(folderCounts[ex.id] || 0);
        const chev = card.querySelector(".folder-chevron");
        if (chev) chev.classList.toggle("collapsed", Boolean(ex.collapsed));
      } else {
        const numEl = card.querySelector(".expr-num");
        if (numEl) numEl.textContent = String(index + 1).padStart(2, "0");

        const dotEl = card.querySelector(".color-dot");
        if (dotEl) {
          dotEl.style.background = getColor(ex.colorIdx);
          dotEl.classList.toggle("hidden-curve", !ex.visible);
        }
      }

      if ((ex.type || "expr") === "expr") {
        syncPlaceholderAndFallback(card, ex);
      }
      updateCardExtras(card, ex, renderedAutoVars);
    });
  }

  function addExpression(initialRaw = "", focusNew = true) {
    const activeObj = expressions.find((e) => e.id === activeExprId);
    const parentFolder = activeObj ? (activeObj.type === "folder" ? activeObj.id : activeObj.folderId || null) : null;
    const ex = {
      id: nextId++,
      type: "expr",
      raw: initialRaw,
      colorIdx: expressions.filter((e) => (e.type || "expr") === "expr").length % PALETTE_DARK.length,
      visible: true,
      lineStyle: "solid",
      lineWidth: 2.4,
      opacity: 1.0,
      showTable: false,
      tableXs: [-2, -1, 0, 1, 2],
      folderId: parentFolder,
      result: null,
    };
    if (parentFolder !== null) {
      let insertIdx = expressions.findIndex((e) => e.id === parentFolder);
      if (insertIdx >= 0) {
        insertIdx += 1;
        while (insertIdx < expressions.length && expressions[insertIdx].folderId === parentFolder) {
          insertIdx++;
        }
        expressions.splice(insertIdx, 0, ex);
      } else {
        expressions.push(ex);
      }
    } else {
      expressions.push(ex);
    }
    if (focusNew) activeExprId = ex.id;
    syncExprCards();
    pushHistory();

    if (focusNew) {
      requestAnimationFrame(() => {
        const card = exprListEl.querySelector(`.expr-card[data-card-id="${ex.id}"]`);
        if (card) card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        const mf = exprListEl.querySelector(`math-field[data-mf-id="${ex.id}"]`);
        const inp = exprListEl.querySelector(`input[data-input-id="${ex.id}"]`);
        if (mf && window.__mathLiveLoaded) { try { mf.focus(); } catch (_) {} }
        else if (inp && settings.showRawInput) inp.focus();
      });
    }
    scheduleCompute(20);
  }

  function addStandaloneTable() {
    const ex = {
      id: nextId++,
      type: "table",
      colorIdx: expressions.length % PALETTE_DARK.length,
      visible: true,
      opacity: 1.0,
      rows: [[0, 1], [1, 3], [2, 5], [3, 7]],
      folderId: null,
      result: null,
    };
    expressions.push(ex);
    activeExprId = ex.id;
    syncExprCards();
    pushHistory();
    scheduleCompute(15);
  }

  function addNote() {
    const ex = {
      id: nextId++,
      type: "note",
      text: "",
      folderId: null,
      result: null,
    };
    expressions.push(ex);
    activeExprId = ex.id;
    syncExprCards();
    pushHistory();
    requestAnimationFrame(() => {
      const card = exprListEl.querySelector(`.expr-card[data-card-id="${ex.id}"]`);
      card?.querySelector("textarea")?.focus();
    });
  }

  function addFolder() {
    const ex = {
      id: nextId++,
      type: "folder",
      title: "Ordner",
      collapsed: false,
      result: null,
    };
    expressions.push(ex);
    activeExprId = ex.id;
    syncExprCards();
    pushHistory();
    requestAnimationFrame(() => {
      const card = exprListEl.querySelector(`.expr-card[data-card-id="${ex.id}"]`);
      const inp = card?.querySelector(".folder-title-input");
      if (inp) { inp.focus(); inp.select(); }
    });
  }

  let lastAnimTime = 0;
  function animLoop(ts) {
    if (ts - lastAnimTime > 48) {
      lastAnimTime = ts;
      let changed = false;

      for (const ex of expressions) {
        if (ex.playing && ex.result && ex.result.kind === "slider") {
          const range = ex.max - ex.min;
          const delta = (range / 110) * (ex.dir || 1);
          let nextVal = ex.result.value + delta;
          if (nextVal >= ex.max) { nextVal = ex.max; ex.dir = -1; }
          if (nextVal <= ex.min) { nextVal = ex.min; ex.dir = 1; }
          ex.result.value = nextVal;
          ex.raw = `${formatVarLatex(ex.result.name)} = ${nextVal.toFixed(2)}`;
          const mf = exprListEl.querySelector(`math-field[data-mf-id="${ex.id}"]`);
          if (mf && window.__mathLiveLoaded && document.activeElement !== mf) {
            try { mf.value = ex.raw; } catch (_) {}
          }
          const inp = exprListEl.querySelector(`input[data-input-id="${ex.id}"]`);
          if (inp && document.activeElement !== inp) inp.value = ex.raw;
          const rng = exprListEl.querySelector(`input[data-explicit-range="${ex.id}"]`);
          if (rng) { rng.value = nextVal; paintSliderTrack(rng, nextVal, ex.min, ex.max); }
          changed = true;
        }
      }

      for (const [vname, st] of Object.entries(autoSliders)) {
        if (!st.playing) continue;
        const range = st.max - st.min;
        const delta = (range / 110) * (st.dir || 1);
        let nextVal = st.value + delta;
        if (nextVal >= st.max) { nextVal = st.max; st.dir = -1; }
        if (nextVal <= st.min) { nextVal = st.min; st.dir = 1; }
        st.value = nextVal;

        const lbl = document.querySelector(`[data-auto-label="${vname}"]`);
        if (lbl) renderLatex(lbl, `${formatVarLatex(vname)} = ${nextVal.toFixed(2)}`);
        const rng = document.querySelector(`[data-auto-range="${vname}"]`);
        if (rng) { rng.value = nextVal; paintSliderTrack(rng, nextVal, st.min, st.max); }
        changed = true;
      }

      if (changed) requestComputeLive();
    }
    requestAnimationFrame(animLoop);
  }
  requestAnimationFrame(animLoop);

  const KEYPAD_TABS = {
    basic: {
      colsClass: "",
      keys: [
        { tex: "x", ins: "x", mf: "x" },
        { tex: "y", ins: "y", mf: "y" },
        { tex: "a^2", ins: "^{2}", mf: "#@^{2}" },
        { tex: "a^b", ins: "^{}", shift: -1, mf: "#@^{#?}" },
        { tex: String.raw`\frac{a}{b}`, ins: String.raw`\frac{}{}`, shift: -3, mf: String.raw`\frac{#@}{#?}` },
        { tex: "7", ins: "7", mf: "7", cls: "key-num" },
        { tex: "8", ins: "8", mf: "8", cls: "key-num" },
        { tex: "9", ins: "9", mf: "9", cls: "key-num" },
        { tex: String.raw`\div`, ins: String.raw` \div `, mf: String.raw`\div`, cls: "key-op" },
        { action: "backspace", icon: ICON_BACKSPACE, cls: "key-op", title: "Löschen" },

        { tex: "(", ins: "(", mf: String.raw`\left(#0\right)` },
        { tex: ")", ins: ")", mf: ")" },
        { tex: String.raw`\sqrt{\square}`, ins: String.raw`\sqrt{}`, shift: -1, mf: String.raw`\sqrt{#0}` },
        { tex: String.raw`\sqrt[n]{\square}`, ins: String.raw`\sqrt[3]{}`, shift: -1, mf: String.raw`\sqrt[#?]{#?}` },
        { tex: "|x|", ins: "||", shift: -1, mf: String.raw`\left|#0\right|` },
        { tex: "4", ins: "4", mf: "4", cls: "key-num" },
        { tex: "5", ins: "5", mf: "5", cls: "key-num" },
        { tex: "6", ins: "6", mf: "6", cls: "key-num" },
        { tex: String.raw`\times`, ins: String.raw` \cdot `, mf: String.raw`\cdot`, cls: "key-op" },
        { tex: "n!", ins: "!", mf: "!", cls: "key-op", title: "Fakultät" },

        { tex: String.raw`\pi`, ins: String.raw`\pi`, mf: String.raw`\pi`, title: "Kreiszahl π" },
        { tex: String.raw`\theta`, ins: String.raw`\theta`, mf: String.raw`\theta` },
        { tex: String.raw`\sum`, ins: String.raw`\sum_{n=1}^{5}()`, shift: -1, mf: String.raw`\sum\limits_{n=#?}^{#?}#?`, title: "Summe (großes Sigma)" },
        { tex: String.raw`\prod`, ins: String.raw`\prod_{n=1}^{5}()`, shift: -1, mf: String.raw`\prod\limits_{n=#?}^{#?}#?`, title: "Produkt (großes Pi)" },
        { tex: String.raw`\int`, ins: String.raw`\int_{0}^{2}() dx`, shift: -4, mf: String.raw`\int_{#?}^{#?}#?\,dx`, title: "Integral" },
        { tex: "1", ins: "1", mf: "1", cls: "key-num" },
        { tex: "2", ins: "2", mf: "2", cls: "key-num" },
        { tex: "3", ins: "3", mf: "3", cls: "key-num" },
        { tex: "-", ins: " - ", mf: "-", cls: "key-op" },
        { tex: String.raw`\frac{d}{dx}`, ins: String.raw`\frac{d}{dx}()`, shift: -1, mf: String.raw`\frac{d}{dx}\left(#0\right)`, cls: "key-op", title: "Ableitung" },

        { tex: String.raw`\le`, ins: String.raw` \le `, mf: String.raw`\le` },
        { tex: String.raw`\ge`, ins: String.raw` \ge `, mf: String.raw`\ge` },
        { tex: "<", ins: " < ", mf: "<" },
        { tex: ">", ins: " > ", mf: ">" },
        { tex: "e", ins: "e", mf: "e" },
        { tex: "0", ins: "0", mf: "0", cls: "key-num" },
        { tex: ".", ins: ".", mf: ".", cls: "key-num" },
        { tex: "=", ins: " = ", mf: "=", cls: "key-op" },
        { tex: "+", ins: " + ", mf: "+", cls: "key-op" },
        { action: "enter", icon: ICON_ENTER, cls: "key-accent", title: "Neue Zeile" },
      ],
    },
    funcs: {
      colsClass: "six-col-grid",
      keys: [
        { tex: String.raw`\sin`, ins: String.raw`\sin()`, shift: -1, mf: String.raw`\sin\left(#0\right)` },
        { tex: String.raw`\cos`, ins: String.raw`\cos()`, shift: -1, mf: String.raw`\cos\left(#0\right)` },
        { tex: String.raw`\tan`, ins: String.raw`\tan()`, shift: -1, mf: String.raw`\tan\left(#0\right)` },
        { tex: String.raw`\arcsin`, ins: String.raw`\arcsin()`, shift: -1, mf: String.raw`\arcsin\left(#0\right)` },
        { tex: String.raw`\arccos`, ins: String.raw`\arccos()`, shift: -1, mf: String.raw`\arccos\left(#0\right)` },
        { tex: String.raw`\arctan`, ins: String.raw`\arctan()`, shift: -1, mf: String.raw`\arctan\left(#0\right)` },

        { tex: String.raw`\sinh`, ins: String.raw`\sinh()`, shift: -1, mf: String.raw`\sinh\left(#0\right)` },
        { tex: String.raw`\cosh`, ins: String.raw`\cosh()`, shift: -1, mf: String.raw`\cosh\left(#0\right)` },
        { tex: String.raw`\tanh`, ins: String.raw`\tanh()`, shift: -1, mf: String.raw`\tanh\left(#0\right)` },
        { tex: String.raw`\sec`, ins: String.raw`\sec()`, shift: -1, mf: String.raw`\sec\left(#0\right)` },
        { tex: String.raw`\csc`, ins: String.raw`\csc()`, shift: -1, mf: String.raw`\csc\left(#0\right)` },
        { tex: String.raw`\cot`, ins: String.raw`\cot()`, shift: -1, mf: String.raw`\cot\left(#0\right)` },

        { tex: String.raw`\ln`, ins: String.raw`\ln()`, shift: -1, mf: String.raw`\ln\left(#0\right)` },
        { tex: String.raw`\log`, ins: String.raw`\log()`, shift: -1, mf: String.raw`\log\left(#0\right)` },
        { tex: String.raw`\log_b`, ins: String.raw`\log_{2}()`, shift: -1, mf: String.raw`\log_{#?}\left(#?\right)` },
        { tex: "e^x", ins: "e^{}", shift: -1, mf: "e^{#?}" },
        { tex: String.raw`\lfloor x \rfloor`, ins: String.raw`\lfloor \rfloor`, shift: -8, mf: String.raw`\lfloor #0 \rfloor` },
        { tex: String.raw`\lceil x \rceil`, ins: String.raw`\lceil \rceil`, shift: -7, mf: String.raw`\lceil #0 \rceil` },

        { tex: String.raw`f(x)`, ins: "f(x) = ", mf: String.raw`f\left(x\right)=` },
        { tex: String.raw`f'(x)`, ins: "f'(x)", mf: String.raw`f'\left(x\right)` },
        { tex: String.raw`r(\theta)`, ins: "r = ", mf: "r=" },
        { tex: String.raw`(x(t),y(t))`, ins: "(, )", shift: -3, mf: String.raw`\left(#?,#?\right)` },
        { tex: String.raw`\int f`, ins: String.raw`\int() dx`, shift: -4, mf: String.raw`\int #?\,dx` },
        { tex: String.raw`\frac{d}{dx}`, ins: String.raw`\frac{d}{dx}()`, shift: -1, mf: String.raw`\frac{d}{dx}\left(#0\right)` },
      ],
    },
    symbols: {
      colsClass: "six-col-grid",
      keys: [
        { tex: String.raw`\sum_{n=a}^{b}`, ins: String.raw`\sum_{n=1}^{5}()`, shift: -1, mf: String.raw`\sum\limits_{n=#?}^{#?}#?` },
        { tex: String.raw`\prod_{n=a}^{b}`, ins: String.raw`\prod_{n=1}^{5}()`, shift: -1, mf: String.raw`\prod\limits_{n=#?}^{#?}#?` },
        { tex: String.raw`\int_{a}^{b}`, ins: String.raw`\int_{0}^{2}() dx`, shift: -4, mf: String.raw`\int_{#?}^{#?}#?\,dx` },
        { tex: String.raw`\infty`, ins: String.raw`\infty`, mf: String.raw`\infty` },
        { tex: String.raw`\pi`, ins: String.raw`\pi`, mf: String.raw`\pi` },
        { tex: String.raw`\theta`, ins: String.raw`\theta`, mf: String.raw`\theta` },

        { tex: String.raw`\sigma`, ins: String.raw`\sigma`, mf: String.raw`\sigma` },
        { tex: String.raw`\mu`, ins: String.raw`\mu`, mf: String.raw`\mu` },
        { tex: String.raw`\alpha`, ins: String.raw`\alpha`, mf: String.raw`\alpha` },
        { tex: String.raw`\beta`, ins: String.raw`\beta`, mf: String.raw`\beta` },
        { tex: String.raw`\phi`, ins: String.raw`\phi`, mf: String.raw`\phi` },
        { tex: String.raw`\omega`, ins: String.raw`\omega`, mf: String.raw`\omega` },

        { tex: String.raw`\Delta`, ins: String.raw`\Delta`, mf: String.raw`\Delta` },
        { tex: "n", ins: "n", mf: "n" },
        { tex: "k", ins: "k", mf: "k" },
        { tex: "t", ins: "t", mf: "t" },
        { tex: "a", ins: "a", mf: "a" },
        { tex: "b", ins: "b", mf: "b" },

        { tex: "c", ins: "c", mf: "c" },
        { tex: "r", ins: "r", mf: "r" },
        { tex: ",", ins: ", ", mf: "," },
        { tex: String.raw`\cdot`, ins: String.raw` \cdot `, mf: String.raw`\cdot`, cls: "key-op" },
        { tex: String.raw`\div`, ins: String.raw` \div `, mf: String.raw`\div`, cls: "key-op" },
        { action: "backspace", icon: ICON_BACKSPACE, cls: "key-op" },
      ],
    },
  };

  function buildKeypad() {
    const grid = document.getElementById("keypadGrid");
    const cfg = KEYPAD_TABS[currentTab];
    grid.className = "keypad-grid" + (cfg.colsClass ? " " + cfg.colsClass : "");
    grid.innerHTML = "";

    for (const k of cfg.keys) {
      const btn = document.createElement("button");
      btn.className = "key-btn" + (k.cls ? " " + k.cls : "");
      if (k.title) btn.title = k.title;

      if (k.icon) btn.innerHTML = k.icon;
      else renderLatex(btn, k.tex);

      btn.addEventListener("mousedown", (e) => {
        e.preventDefault();
        if (k.action === "enter") { addExpression(""); return; }

        const card = exprListEl.querySelector(`.expr-card[data-card-id="${activeExprId}"]`);
        const mf = exprListEl.querySelector(`math-field[data-mf-id="${activeExprId}"]`);
        const inp = exprListEl.querySelector(`input[data-input-id="${activeExprId}"]`);
        const ex = expressions.find((item) => item.id === activeExprId);
        if (!ex || !card) return;

        if (inp && ((settings.showRawInput && document.activeElement === inp) || !window.__mathLiveLoaded)) {
          const start = inp.selectionStart ?? inp.value.length;
          const end = inp.selectionEnd ?? inp.value.length;
          if (k.action === "backspace") {
            if (start !== end) {
              inp.value = inp.value.slice(0, start) + inp.value.slice(end);
              inp.setSelectionRange(start, start);
            } else if (start > 0) {
              inp.value = inp.value.slice(0, start - 1) + inp.value.slice(end);
              inp.setSelectionRange(start - 1, start - 1);
            }
          } else {
            inp.value = inp.value.slice(0, start) + k.ins + inp.value.slice(end);
            const newPos = start + k.ins.length + (k.shift || 0);
            inp.setSelectionRange(newPos, newPos);
          }
          ex.raw = inp.value;
          if (mf && window.__mathLiveLoaded) { try { mf.value = ex.raw; } catch (_) {} }
          syncPlaceholderAndFallback(card, ex);
          inp.focus();
          scheduleCompute(90);
          scheduleHistoryPush();
          return;
        }

        if (mf && window.__mathLiveLoaded) {
          try {
            mf.focus();
            if (k.action === "backspace") {
              mf.executeCommand("deleteBackward");
            } else {
              const tpl = k.mf ?? k.ins;
              const hasSlot = tpl.includes("#?") || tpl.includes("#0");
              const opts = { selectionMode: hasSlot ? "placeholder" : "after" };
              if (typeof mf.insert === "function") mf.insert(tpl, opts);
              else if (typeof mf.executeCommand === "function") mf.executeCommand(["insert", tpl, opts]);
            }
            ex.raw = mf.value || "";
            if (inp) inp.value = ex.raw;
            syncPlaceholderAndFallback(card, ex);
            scheduleCompute(90);
            scheduleHistoryPush();
          } catch (_) {}
        }
      });
      grid.append(btn);
    }
  }

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      currentTab = btn.dataset.tab;
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
      buildKeypad();
    });
  });


"""


def get_sidebar_css() -> str:
    return SIDEBAR_CSS


def get_sidebar_html() -> str:
    return SIDEBAR_HTML


def get_sidebar_js() -> str:
    return SIDEBAR_JS

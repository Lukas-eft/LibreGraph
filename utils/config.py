from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    window_title: str = "Graphing Calculator"
    window_width: int = 1360
    window_height: int = 860
    window_min_width: int = 900
    window_min_height: int = 600
    host: str = "127.0.0.1"
    port: int = 0
    dark_background: str = "#09090b"


@dataclass(frozen=True)
class ViewportConfig:
    default_scale: float = 72.0
    min_scale: float = 1e-250
    max_scale: float = 1e12
    max_world_bound: float = 1e290


@dataclass(frozen=True)
class SamplingConfig:
    base_samples_1d: int = 920
    max_adaptive_points: int = 3400
    overscan_ratio: float = 0.35
    parametric_samples: int = 1200
    polar_samples: int = 1400
    implicit_nx: int = 171
    implicit_ny: int = 129
    shade_mx: int = 128
    shade_my: int = 96
    surface_nx: int = 36
    surface_ny: int = 36
    slope_nx: int = 22
    slope_ny: int = 16
    max_sum_terms: int = 120
    max_list_items: int = 30
    max_key_points_per_type: int = 20


APP_CONFIG = AppConfig()
VIEWPORT_CONFIG = ViewportConfig()
SAMPLING_CONFIG = SamplingConfig()

PALETTE_DARK: tuple[str, ...] = (
    "#fafafa",
    "#a1a1aa",
    "#60a5fa",
    "#34d399",
    "#f59e0b",
    "#f472b6",
    "#a78bfa",
    "#fb923c",
)

PALETTE_LIGHT: tuple[str, ...] = (
    "#18181b",
    "#71717a",
    "#2563eb",
    "#059669",
    "#d97706",
    "#db2777",
    "#7c3aed",
    "#ea580c",
)

DEFAULT_SETTINGS: dict[str, bool] = {
    "showRawInput": True,
    "autoSliders": True,
    "showGrid": True,
    "polarGrid": False,
    "showAxisLabels": True,
    "showCoordHud": True,
    "showKeyPoints": True,
    "showTangent": True,
}

from __future__ import annotations

from dataclasses import dataclass

from utils.config import VIEWPORT_CONFIG


def format_coord(val: float) -> float:
    f = float(val)
    if f == 0.0:
        return 0.0
    return float(f"{f:.12g}")


@dataclass(frozen=True)
class ViewportBounds:

    xmin: float
    xmax: float
    ymin: float
    ymax: float

    @property
    def x_span(self) -> float:
        return max(self.xmax - self.xmin, 1e-300)

    @property
    def y_span(self) -> float:
        return max(self.ymax - self.ymin, 1e-300)

    @property
    def cx(self) -> float:
        return 0.5 * (self.xmin + self.xmax)

    @property
    def cy(self) -> float:
        return 0.5 * (self.ymin + self.ymax)

    def contains_origin(self) -> bool:
        return self.xmin <= 0.0 <= self.xmax and self.ymin <= 0.0 <= self.ymax

    def world_to_screen(self, x: float, y: float, width: float, height: float) -> tuple[float, float]:
        scale_x = width / self.x_span
        scale_y = height / self.y_span
        sx = (x - self.xmin) * scale_x
        sy = (self.ymax - y) * scale_y
        return sx, sy

    def screen_to_world(self, sx: float, sy: float, width: float, height: float) -> tuple[float, float]:
        x = self.xmin + (sx / max(width, 1.0)) * self.x_span
        y = self.ymax - (sy / max(height, 1.0)) * self.y_span
        return x, y

    @classmethod
    def from_dict(cls, raw: dict) -> "ViewportBounds":
        limit = VIEWPORT_CONFIG.max_world_bound

        def _clamp(v: float) -> float:
            return max(-limit, min(limit, float(v)))

        xmin = _clamp(raw["xmin"])
        xmax = _clamp(raw["xmax"])
        ymin = _clamp(raw["ymin"])
        ymax = _clamp(raw["ymax"])
        if xmax <= xmin:
            xmax = xmin + 1e-6
        if ymax <= ymin:
            ymax = ymin + 1e-6
        return cls(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)

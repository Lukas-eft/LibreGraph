from __future__ import annotations

import math
import re

import numpy as np
import sympy as sp

from math_engine.parser import (
    BASE_NUMPY_MAP,
    BUILTIN_FUNC_NAMES,
    R_SYM,
    RESERVED_SYMS,
    T_SYM,
    THETA_SYM,
    U_SYM,
    V_SYM,
    X_SYM,
    Y_SYM,
    Z_SYM,
    _parse_symbolic,
    extract_domain_restrictions,
    extract_inline_lists,
    extract_z_plane_restriction,
    nthroot,
    parse_domain_conditions,
    parse_list_definition,
    parse_ode_equation,
    parse_piecewise_rhs,
    parse_regression_expr,
    parse_single_condition_chain,
    parse_surface_3d,
    preprocess_latex,
    split_top_level_comma,
    split_top_level_tuple,
)
from math_engine.viewport import ViewportBounds, format_coord
from utils.config import SAMPLING_CONFIG


def _expand_named_funcs(expr, named_funcs: dict, num_registry: dict, depth: int = 0):
    if depth > 8 or not named_funcs:
        return expr

    def _replace_node(node):
        if not node.args:
            return node
        new_args = tuple(_replace_node(a) for a in node.args)
        fname = getattr(node.func, "_user_fname", None)
        if fname is not None and fname in named_funcs and len(new_args) == 1:
            order = getattr(node.func, "_user_order", 0)
            finfo = named_funcs[fname]
            psym = finfo["var"]
            fexpr = finfo["expr"]
            arg = new_args[0]

            if order == 0:
                expanded = fexpr.subs(psym, arg)
                return _expand_named_funcs(expanded, named_funcs, num_registry, depth + 1)

            sym_ok = False
            dexpr = None
            try:
                diffable = fexpr.replace(nthroot, lambda a, n: a ** (sp.Integer(1) / n))
                diffable = _prepare_for_lambdify(diffable)
                dexpr = sp.diff(diffable, psym, order)
                unsupported = (sp.Derivative, sp.polygamma, sp.DiracDelta, sp.Heaviside)
                if not dexpr.has(*unsupported):
                    sym_ok = True
            except Exception:
                sym_ok = False

            if sym_ok and dexpr is not None:
                expanded = dexpr.subs(psym, arg)
                return _expand_named_funcs(expanded, named_funcs, num_registry, depth + 1)

            reg_key = f"__numd{order}_{fname}"
            if reg_key not in num_registry:
                base_ev = _prepare_for_lambdify(fexpr)
                base_fn = sp.lambdify(psym, base_ev, modules=[BASE_NUMPY_MAP, "numpy"])

                def _make_num_deriv(bfn, ord_k):
                    def _nd(u):
                        ua = np.asarray(u, dtype=float)
                        with np.errstate(all="ignore"):
                            if ord_k == 1:
                                h = np.maximum(np.abs(ua) * 1e-6, 1e-5)
                                return (bfn(ua + h) - bfn(ua - h)) / (2.0 * h)
                            if ord_k == 2:
                                h = np.maximum(np.abs(ua) * 1e-4, 1e-4)
                                return (bfn(ua + h) - 2.0 * bfn(ua) + bfn(ua - h)) / (h * h)
                            h = np.maximum(np.abs(ua) * 1e-3, 1e-3)
                            return (
                                bfn(ua + 2.0 * h)
                                - 2.0 * bfn(ua + h)
                                + 2.0 * bfn(ua - h)
                                - bfn(ua - 2.0 * h)
                            ) / (2.0 * (h ** 3))

                    return _nd

                num_registry[reg_key] = _make_num_deriv(base_fn, order)

            return sp.Function(reg_key)(arg)

        return node.func(*new_args)

    return _replace_node(expr)


def _substitute_params(expr, values_map: dict):
    if not values_map:
        return expr
    subs = {}
    for sym in expr.free_symbols:
        name = str(sym)
        if name in values_map:
            fval = float(values_map[name])
            if abs(fval - round(fval)) < 1e-9:
                subs[sym] = sp.Integer(int(round(fval)))
            else:
                subs[sym] = sp.Float(fval)
    return expr.subs(subs) if subs else expr


def _prepare_for_lambdify(expr):
    for node in list(expr.atoms(sp.Sum, sp.Product)):
        empty_range = False
        new_limits = []
        for v, low, high in node.limits:
            if low.is_number and high.is_number:
                lo_i = int(round(float(low.evalf())))
                hi_i = int(round(float(high.evalf())))
                if lo_i > hi_i:
                    empty_range = True
                    break
                if hi_i - lo_i > SAMPLING_CONFIG.max_sum_terms:
                    raise ValueError("Max. 120 Terme für Summe/Produkt")
                new_limits.append((v, sp.Integer(lo_i), sp.Integer(hi_i)))
            else:
                new_limits.append((v, low, high))

        if empty_range:
            neutral = sp.Integer(0) if isinstance(node, sp.Sum) else sp.Integer(1)
            expr = expr.xreplace({node: neutral})
        else:
            expr = expr.xreplace({node: node.func(node.function, *new_limits)})

    if expr.has(sp.Sum, sp.Product, sp.Integral, sp.Derivative):
        expr = expr.doit()
    return expr


def _eval_numeric(func, shape, *args):
    with np.errstate(all="ignore"):
        val = func(*args)
    arr = np.asarray(val)
    if np.iscomplexobj(arr):
        real_arr = np.where(np.abs(np.imag(arr)) < 1e-7, np.real(arr), np.nan)
        arr = real_arr.astype(float)
    else:
        arr = arr.astype(float)
    arr = np.broadcast_to(arr, shape).copy()
    arr[~np.isfinite(arr)] = np.nan
    return arr


def _build_domain_mask_fn(domain_chains: list, finalize_fn, num_registry: dict):
    if not domain_chains:
        return None, []

    compiled = []
    boundary_xs: list[float] = []
    mods = [num_registry, "numpy"]

    for lhs, op, rhs in domain_chains:
        lhs_ev = _prepare_for_lambdify(finalize_fn(lhs))
        rhs_ev = _prepare_for_lambdify(finalize_fn(rhs))
        diff = lhs_ev - rhs_ev

        if lhs_ev == X_SYM and not rhs_ev.free_symbols:
            try:
                bval = float(rhs_ev.evalf())
                if math.isfinite(bval):
                    boundary_xs.append(bval)
            except Exception:
                pass
        elif rhs_ev == X_SYM and not lhs_ev.free_symbols:
            try:
                bval = float(lhs_ev.evalf())
                if math.isfinite(bval):
                    boundary_xs.append(bval)
            except Exception:
                pass

        fn = sp.lambdify((X_SYM, Y_SYM, T_SYM, THETA_SYM), diff, modules=mods)
        compiled.append((fn, op))

    def _mask(x_arr, y_arr, t_arr=None, theta_arr=None):
        xa = np.asarray(x_arr, dtype=float)
        ya = np.asarray(y_arr, dtype=float)
        shape = np.broadcast(xa, ya).shape
        ta = np.zeros(shape, dtype=float) if t_arr is None else np.broadcast_to(np.asarray(t_arr, dtype=float), shape)
        tha = np.zeros(shape, dtype=float) if theta_arr is None else np.broadcast_to(np.asarray(theta_arr, dtype=float), shape)
        m = np.ones(shape, dtype=bool)
        for cfn, cop in compiled:
            dv = _eval_numeric(cfn, shape, xa, ya, ta, tha)
            m &= np.isfinite(dv)
            if cop == "<":
                m &= dv < 0.0
            elif cop == "<=":
                m &= dv <= 1e-12
            elif cop == ">":
                m &= dv > 0.0
            else:
                m &= dv >= -1e-12
        return m

    return _mask, boundary_xs


def _format_domain_latex(domain_chains: list) -> str:
    if not domain_chains:
        return ""
    op_map = {"<=": r"\le", ">=": r"\ge", "<": "<", ">": ">"}
    parts = [f"{sp.latex(l)} {op_map[o]} {sp.latex(r)}" for l, o, r in domain_chains]
    return r"\left\{" + r",\; ".join(parts) + r"\right\}"


_MS_TABLE = {
    1: [(3, 0)],
    2: [(0, 1)],
    3: [(3, 1)],
    4: [(1, 2)],
    5: [(3, 0), (1, 2)],
    6: [(0, 2)],
    7: [(3, 2)],
    8: [(2, 3)],
    9: [(0, 2)],
    10: [(0, 1), (2, 3)],
    11: [(1, 2)],
    12: [(1, 3)],
    13: [(0, 1)],
    14: [(3, 0)],
}


def marching_squares(X: np.ndarray, Y: np.ndarray, Z: np.ndarray) -> list:
    v0 = Z[:-1, :-1]
    v1 = Z[:-1, 1:]
    v2 = Z[1:, 1:]
    v3 = Z[1:, :-1]

    valid = np.isfinite(v0) & np.isfinite(v1) & np.isfinite(v2) & np.isfinite(v3)

    idx = (
        (v0 > 0).astype(np.uint8)
        | ((v1 > 0).astype(np.uint8) << 1)
        | ((v2 > 0).astype(np.uint8) << 2)
        | ((v3 > 0).astype(np.uint8) << 3)
    )
    active = valid & (idx != 0) & (idx != 15)
    rows, cols = np.nonzero(active)
    if len(rows) == 0:
        return []

    x0 = X[rows, cols]
    x1 = X[rows, cols + 1]
    y0 = Y[rows, cols]
    y1 = Y[rows + 1, cols]

    a0 = v0[rows, cols]
    a1 = v1[rows, cols]
    a2 = v2[rows, cols]
    a3 = v3[rows, cols]
    cases = idx[rows, cols]

    def interp(va, vb):
        denom = va - vb
        tol = np.maximum(np.abs(va), np.abs(vb)) * 1e-12 + 1e-300
        good = np.abs(denom) > tol
        safe = np.where(good, denom, 1.0)
        t = np.where(good, va / safe, 0.5)
        return np.clip(t, 0.0, 1.0)

    t0 = interp(a0, a1)
    t1 = interp(a1, a2)
    t2 = interp(a3, a2)
    t3 = interp(a0, a3)

    ex = [x0 + t0 * (x1 - x0), x1, x0 + t2 * (x1 - x0), x0]
    ey = [y0, y0 + t1 * (y1 - y0), y1, y0 + t3 * (y1 - y0)]

    segments = []
    for k in range(len(rows)):
        for e_a, e_b in _MS_TABLE[int(cases[k])]:
            segments.append(
                [
                    format_coord(ex[e_a][k]),
                    format_coord(ey[e_a][k]),
                    format_coord(ex[e_b][k]),
                    format_coord(ey[e_b][k]),
                ]
            )
    return segments


_GREEK_PARAM_NAMES = {"alpha", "beta", "sigma", "mu", "phi", "omega", "Delta", "theta"}
_ALWAYS_CONST_SYMS = {"e", "pi", "oo"}
_NON_SLIDER_LHS = {"x", "y", "z", "e", "pi", "oo"}


def _is_valid_slider_name(name: str) -> bool:
    if name in _NON_SLIDER_LHS or name in BUILTIN_FUNC_NAMES:
        return False
    if len(name) == 1 and name.isalpha():
        return True
    if name in _GREEK_PARAM_NAMES:
        return True
    if "_" in name and re.match(r"^[a-zA-Z]+_[a-zA-Z0-9_]+$", name):
        return True
    return False


def _extract_param_bounds(domain_chains: list, param_sym, finalize_fn, default_lo: float, default_hi: float) -> tuple[float, float]:
    lo, hi = None, None
    for lhs, op, rhs in domain_chains:
        l_ev = _prepare_for_lambdify(finalize_fn(lhs))
        r_ev = _prepare_for_lambdify(finalize_fn(rhs))
        if l_ev == param_sym and not r_ev.free_symbols:
            v = float(r_ev.evalf())
            if math.isfinite(v):
                if op in (">", ">="):
                    lo = v if lo is None else max(lo, v)
                else:
                    hi = v if hi is None else min(hi, v)
        elif r_ev == param_sym and not l_ev.free_symbols:
            v = float(l_ev.evalf())
            if math.isfinite(v):
                if op in ("<", "<="):
                    lo = v if lo is None else max(lo, v)
                else:
                    hi = v if hi is None else min(hi, v)
    return (lo if lo is not None else default_lo, hi if hi is not None else default_hi)


def _detect_auto_vars(
    exprs: list,
    explicit_params: dict,
    named_funcs: dict,
    list_params: dict | None = None,
    bound_vars: set[str] | None = None,
) -> list:
    lp = list_params or {}
    blocked = _ALWAYS_CONST_SYMS | (bound_vars if bound_vars is not None else {"x", "y", "z"})
    found = set()
    for ex in exprs:
        for sym in ex.free_symbols:
            name = str(sym)
            if (
                name not in blocked
                and name not in explicit_params
                and name not in named_funcs
                and name not in lp
            ):
                found.add(name)
    return sorted(found)


def _detect_used_lists(exprs: list, list_params: dict) -> list[str]:
    if not list_params:
        return []
    used = set()
    for ex in exprs:
        for sym in ex.free_symbols:
            name = str(sym)
            if name in list_params:
                used.add(name)
    return sorted(used)


def _eval_scalar_masked(fn, domain_fn, x: float) -> float:
    y = float(_eval_numeric(fn, (1,), np.array([x]))[0])
    if not math.isfinite(y):
        return float("nan")
    if domain_fn is not None:
        ok = bool(domain_fn(np.array([x]), np.array([y]))[0])
        if not ok:
            return float("nan")
    return y


def _bisect_root(g_fn, a: float, b: float, ga: float, gb: float, iters: int = 22) -> float | None:
    lo, hi = a, b
    glo, ghi = ga, gb
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if mid == lo or mid == hi:
            break
        gm = g_fn(mid)
        if not math.isfinite(gm):
            return None
        if abs(gm) <= 1e-13:
            return mid
        if (glo <= 0.0 <= gm) or (gm <= 0.0 <= glo):
            hi, ghi = mid, gm
        else:
            lo, glo = mid, gm
    mid = 0.5 * (lo + hi)
    gm = g_fn(mid)
    if not math.isfinite(gm):
        return None
    if abs(gm) > max(abs(ga), abs(gb)) * 0.25 + 1e-4:
        return None
    return mid


def _golden_extremum(f_fn, a: float, b: float, find_max: bool, iters: int = 22) -> tuple[float, float] | None:
    phi = (math.sqrt(5.0) - 1.0) / 2.0
    lo, hi = a, b
    c = hi - phi * (hi - lo)
    d = lo + phi * (hi - lo)
    fc = f_fn(c)
    fd = f_fn(d)
    for _ in range(iters):
        if not (math.isfinite(fc) and math.isfinite(fd)):
            return None
        if (fc > fd) if find_max else (fc < fd):
            hi = d
            d = c
            fd = fc
            c = hi - phi * (hi - lo)
            fc = f_fn(c)
        else:
            lo = c
            c = d
            fc = fd
            d = lo + phi * (hi - lo)
            fd = f_fn(d)
    xm = 0.5 * (lo + hi)
    ym = f_fn(xm)
    if not math.isfinite(ym):
        return None
    return xm, ym


def _dedup_keypoints(kps: list[dict], x_tol: float, y_tol: float, max_per_type: int) -> list[dict]:
    out: list[dict] = []
    counts: dict[str, int] = {}
    for kp in kps:
        t = kp["type"]
        if counts.get(t, 0) >= max_per_type:
            continue
        dup = False
        for prev in out:
            if abs(prev["x"] - kp["x"]) <= x_tol and abs(prev["y"] - kp["y"]) <= y_tol:
                if prev["type"] == "intercept" and kp["type"] in ("root", "intersection"):
                    prev["type"] = kp["type"]
                dup = True
                break
        if not dup:
            out.append(kp)
            counts[t] = counts.get(t, 0) + 1
    return out


def _compute_curve_keypoints(fn, domain_fn, vp: ViewportBounds) -> list[dict]:
    xmin, xmax, ymin, ymax = vp.xmin, vp.xmax, vp.ymin, vp.ymax
    x_span, y_span = vp.x_span, vp.y_span
    xs = np.linspace(xmin, xmax, 420)
    ys = _eval_numeric(fn, xs.shape, xs)
    if domain_fn is not None:
        ys[~domain_fn(xs, ys)] = np.nan

    f_scalar = lambda u: _eval_scalar_masked(fn, domain_fn, u)
    kps: list[dict] = []

    if xmin <= 0.0 <= xmax:
        y0 = f_scalar(0.0)
        if math.isfinite(y0) and ymin <= y0 <= ymax:
            kp_type = "root" if abs(y0) <= y_span * 1e-6 else "intercept"
            kps.append({"x": 0.0, "y": format_coord(0.0 if kp_type == "root" else y0), "type": kp_type})

    for i in range(len(xs) - 1):
        y0, y1 = float(ys[i]), float(ys[i + 1])
        if not (math.isfinite(y0) and math.isfinite(y1)):
            continue
        if abs(y1 - y0) > 0.9 * y_span:
            continue
        if y0 == 0.0:
            if ymin <= 0.0 <= ymax:
                kps.append({"x": format_coord(xs[i]), "y": 0.0, "type": "root"})
        elif y0 * y1 < 0.0:
            rx = _bisect_root(f_scalar, float(xs[i]), float(xs[i + 1]), y0, y1)
            if rx is not None and xmin <= rx <= xmax and ymin <= 0.0 <= ymax:
                kps.append({"x": format_coord(rx), "y": 0.0, "type": "root"})

    for i in range(1, len(xs) - 1):
        yl, ym, yr = float(ys[i - 1]), float(ys[i]), float(ys[i + 1])
        if not (math.isfinite(yl) and math.isfinite(ym) and math.isfinite(yr)):
            continue
        if abs(ym - yl) > 0.45 * y_span or abs(yr - ym) > 0.45 * y_span:
            continue
        is_max = (ym > yl) and (ym >= yr) and ((ym - yl) > y_span * 1e-7 or (ym - yr) > y_span * 1e-7)
        is_min = (ym < yl) and (ym <= yr) and ((yl - ym) > y_span * 1e-7 or (yr - ym) > y_span * 1e-7)
        if not (is_max or is_min):
            continue
        ext = _golden_extremum(f_scalar, float(xs[i - 1]), float(xs[i + 1]), find_max=is_max)
        if ext is None:
            continue
        ex_x, ex_y = ext
        if xmin <= ex_x <= xmax and ymin <= ex_y <= ymax:
            if abs(ex_y) <= y_span * 1e-5:
                kps.append({"x": format_coord(ex_x), "y": 0.0, "type": "root"})
            else:
                kps.append({"x": format_coord(ex_x), "y": format_coord(ex_y), "type": "extrema"})

    return _dedup_keypoints(kps, x_span * 2e-3, y_span * 2e-3, SAMPLING_CONFIG.max_key_points_per_type)


def _compute_intersections(curve_a: dict, curve_b: dict, vp: ViewportBounds) -> list[dict]:
    xmin, xmax, ymin, ymax = vp.xmin, vp.xmax, vp.ymin, vp.ymax
    x_span, y_span = vp.x_span, vp.y_span
    xs = np.linspace(xmin, xmax, 360)

    fa, da = curve_a["fn"], curve_a["domain_fn"]
    fb, db = curve_b["fn"], curve_b["domain_fn"]

    ya = _eval_numeric(fa, xs.shape, xs)
    yb = _eval_numeric(fb, xs.shape, xs)
    if da is not None:
        ya[~da(xs, ya)] = np.nan
    if db is not None:
        yb[~db(xs, yb)] = np.nan

    diff = ya - yb

    def _diff_scalar(u: float) -> float:
        va = _eval_scalar_masked(fa, da, u)
        vb = _eval_scalar_masked(fb, db, u)
        if not (math.isfinite(va) and math.isfinite(vb)):
            return float("nan")
        return va - vb

    pts: list[dict] = []
    for i in range(len(xs) - 1):
        d0, d1 = float(diff[i]), float(diff[i + 1])
        if not (math.isfinite(d0) and math.isfinite(d1)):
            continue
        if abs(d1 - d0) > 0.9 * y_span:
            continue
        rx = None
        if abs(d0) <= y_span * 1e-9:
            rx = float(xs[i])
        elif d0 * d1 < 0.0:
            rx = _bisect_root(_diff_scalar, float(xs[i]), float(xs[i + 1]), d0, d1)
        if rx is not None and xmin <= rx <= xmax:
            ry = _eval_scalar_masked(fa, da, rx)
            if math.isfinite(ry) and ymin <= ry <= ymax:
                pts.append({"x": format_coord(rx), "y": format_coord(ry), "type": "intersection"})

    return _dedup_keypoints(pts, x_span * 2e-3, y_span * 2e-3, SAMPLING_CONFIG.max_key_points_per_type)


def _eval_definite_integral_area(
    integral_node: sp.Integral,
    vp: ViewportBounds,
    latex_str: str,
    num_registry: dict,
) -> dict | None:
    if len(integral_node.limits) != 1:
        return None
    lim = integral_node.limits[0]
    if len(lim) != 3:
        return None
    var_sym, low_e, high_e = lim
    if low_e.free_symbols or high_e.free_symbols:
        return None

    a_val = float(low_e.evalf())
    b_val = float(high_e.evalf())
    if not (math.isfinite(a_val) and math.isfinite(b_val)):
        return None

    integrand = integral_node.function
    fn = sp.lambdify(var_sym, _prepare_for_lambdify(integrand), modules=[num_registry, "numpy"])

    lo, hi = (a_val, b_val) if a_val <= b_val else (b_val, a_val)
    xs = np.linspace(lo, hi, 260) if hi > lo else np.array([lo])
    ys = _eval_numeric(fn, xs.shape, xs)

    area_val = float("nan")
    try:
        done = integral_node.doit()
        if not done.has(sp.Integral):
            v = complex(done.evalf())
            if abs(v.imag) < 1e-7 and math.isfinite(v.real):
                area_val = float(v.real)
    except Exception:
        pass

    if not math.isfinite(area_val):
        fine_x = np.linspace(lo, hi, 1000) if hi > lo else np.array([lo])
        fine_y = _eval_numeric(fn, fine_x.shape, fine_x)
        fin = np.isfinite(fine_y)
        if np.sum(fin) >= 2:
            raw_trap = float(np.trapezoid(fine_y[fin], fine_x[fin])) if hasattr(np, "trapezoid") else float(np.trapz(fine_y[fin], fine_x[fin]))
            area_val = raw_trap if a_val <= b_val else -raw_trap
        elif hi == lo:
            area_val = 0.0

    if not math.isfinite(area_val):
        return None

    pts = [[format_coord(x), format_coord(y)] if math.isfinite(y) else None for x, y in zip(xs, ys)]
    return {
        "kind": "integral_area",
        "value": format_coord(area_val),
        "bounds": [format_coord(a_val), format_coord(b_val)],
        "points": pts,
        "latex": latex_str,
    }


def _eval_slope_field(rhs_expr, vp: ViewportBounds, latex_str: str, num_registry: dict, domain_fn=None) -> dict:
    ev = _prepare_for_lambdify(rhs_expr)
    fn = sp.lambdify((X_SYM, Y_SYM), ev, modules=[num_registry, "numpy"])
    nx = SAMPLING_CONFIG.slope_nx
    ny = SAMPLING_CONFIG.slope_ny
    dx = vp.x_span / nx
    dy = vp.y_span / ny
    gx = np.linspace(vp.xmin + 0.5 * dx, vp.xmax - 0.5 * dx, nx)
    gy = np.linspace(vp.ymin + 0.5 * dy, vp.ymax - 0.5 * dy, ny)
    X, Y = np.meshgrid(gx, gy)
    S = _eval_numeric(fn, X.shape, X, Y)
    if domain_fn is not None:
        S[~domain_fn(X, Y)] = np.nan

    arrows = []
    for r in range(ny):
        for c in range(nx):
            sv = float(S[r, c])
            if math.isfinite(sv):
                arrows.append([format_coord(X[r, c]), format_coord(Y[r, c]), format_coord(sv)])

    return {
        "kind": "slope_field",
        "arrows": arrows,
        "step_x": format_coord(dx),
        "step_y": format_coord(dy),
        "latex": latex_str,
    }


def _eval_surface_3d(rhs_expr, vp: ViewportBounds, latex_str: str, num_registry: dict, domain_fn=None) -> dict:
    ev = _prepare_for_lambdify(rhs_expr)
    fn = sp.lambdify((X_SYM, Y_SYM), ev, modules=[num_registry, "numpy"])
    nx = SAMPLING_CONFIG.surface_nx
    ny = SAMPLING_CONFIG.surface_ny

    half = min(max(0.5 * min(vp.x_span, vp.y_span), 1e-6), 1e120)
    gx = np.linspace(vp.cx - half, vp.cx + half, nx)
    gy = np.linspace(vp.cy - half, vp.cy + half, ny)
    X, Y = np.meshgrid(gx, gy)
    Z = _eval_numeric(fn, X.shape, X, Y)
    if domain_fn is not None:
        Z[~domain_fn(X, Y)] = np.nan

    fin = np.isfinite(Z)
    if np.any(fin):
        zmin = float(np.percentile(Z[fin], 2))
        zmax = float(np.percentile(Z[fin], 98))
        if abs(zmax - zmin) < 1e-9:
            zmin -= 1.0
            zmax += 1.0
    else:
        zmin, zmax = -1.0, 1.0

    gz = [
        [format_coord(Z[r, c]) if math.isfinite(Z[r, c]) else None for c in range(nx)]
        for r in range(ny)
    ]
    return {
        "kind": "surface3d",
        "gx": [format_coord(v) for v in gx],
        "gy": [format_coord(v) for v in gy],
        "gz": gz,
        "zmin": format_coord(zmin),
        "zmax": format_coord(zmax),
        "latex": latex_str,
    }


def _eval_parametric_surface_3d(ex_x, ex_y, ex_z, latex_str: str, num_registry: dict) -> dict:
    mods = [num_registry, "numpy"]
    fx = sp.lambdify((U_SYM, V_SYM), _prepare_for_lambdify(ex_x), modules=mods)
    fy = sp.lambdify((U_SYM, V_SYM), _prepare_for_lambdify(ex_y), modules=mods)
    fz = sp.lambdify((U_SYM, V_SYM), _prepare_for_lambdify(ex_z), modules=mods)

    nu = SAMPLING_CONFIG.surface_nx
    nv = SAMPLING_CONFIG.surface_ny
    us = np.linspace(0.0, 2.0 * np.pi, nu)
    vs = np.linspace(0.0, 2.0 * np.pi, nv)
    U, V = np.meshgrid(us, vs)

    X = _eval_numeric(fx, U.shape, U, V)
    Y = _eval_numeric(fy, U.shape, U, V)
    Z = _eval_numeric(fz, U.shape, U, V)

    fin = np.isfinite(X) & np.isfinite(Y) & np.isfinite(Z)
    if np.any(fin):
        zmin = float(np.min(Z[fin]))
        zmax = float(np.max(Z[fin]))
        if abs(zmax - zmin) < 1e-9:
            zmin -= 1.0
            zmax += 1.0
    else:
        zmin, zmax = -1.0, 1.0

    def _pack_grid(arr: np.ndarray) -> list:
        return [
            [format_coord(arr[r, c]) if fin[r, c] else None for c in range(nu)]
            for r in range(nv)
        ]

    return {
        "kind": "parametric_surface3d",
        "X": _pack_grid(X),
        "Y": _pack_grid(Y),
        "Z": _pack_grid(Z),
        "zmin": format_coord(zmin),
        "zmax": format_coord(zmax),
        "latex": latex_str,
    }


def _find_axis_extent_3d(fn, axis: int, default_half: float) -> tuple[float, float] | None:
    hi_lin = min(default_half, 10.0)
    hi_exp = math.log10(max(default_half, 10.0))
    mags = np.unique(np.concatenate([
        np.linspace(0.0, hi_lin, 80),
        np.power(10.0, np.linspace(-3.0, min(hi_exp, 6.0), 60)),
    ]))
    pts = np.unique(np.concatenate([-mags[::-1], mags]))
    zeros = np.zeros_like(pts)
    if axis == 0:
        vals = _eval_numeric(fn, pts.shape, pts, zeros, zeros)
    elif axis == 1:
        vals = _eval_numeric(fn, pts.shape, zeros, pts, zeros)
    else:
        vals = _eval_numeric(fn, pts.shape, zeros, zeros, pts)

    fin = np.isfinite(vals[:-1]) & np.isfinite(vals[1:])
    cross = fin & ((vals[:-1] > 0) != (vals[1:] > 0))
    idxs = np.nonzero(cross)[0]
    if len(idxs) == 0:
        return None
    lo = float(pts[idxs[0]])
    hi = float(pts[idxs[-1] + 1])
    span = max(hi - lo, abs(lo), abs(hi), 1e-3)
    margin = 0.20 * span
    return lo - margin, hi + margin


def _eval_implicit_3d(diff_expr, vp: ViewportBounds, latex_str: str, num_registry: dict) -> dict:
    ev = _prepare_for_lambdify(diff_expr)
    fn = sp.lambdify((X_SYM, Y_SYM, Z_SYM), ev, modules=[num_registry, "numpy"])

    half = min(max(0.5 * min(vp.x_span, vp.y_span), 1e-4), 1e6)
    bx = _find_axis_extent_3d(fn, 0, half) or (vp.cx - half, vp.cx + half)
    by = _find_axis_extent_3d(fn, 1, half) or (vp.cy - half, vp.cy + half)
    bz = _find_axis_extent_3d(fn, 2, half) or (-half, half)

    nx = ny = nz = 24
    gx = np.linspace(bx[0], bx[1], nx)
    gy = np.linspace(by[0], by[1], ny)
    gz = np.linspace(bz[0], bz[1], nz)
    X3, Y3, Z3 = np.meshgrid(gx, gy, gz, indexing="ij")
    F = _eval_numeric(fn, X3.shape, X3, Y3, Z3)

    c000 = F[:-1, :-1, :-1]
    c100 = F[1:,  :-1, :-1]
    c010 = F[:-1, 1:,  :-1]
    c110 = F[1:,  1:,  :-1]
    c001 = F[:-1, :-1, 1:]
    c101 = F[1:,  :-1, 1:]
    c011 = F[:-1, 1:,  1:]
    c111 = F[1:,  1:,  1:]

    valid = (
        np.isfinite(c000) & np.isfinite(c100) & np.isfinite(c010) & np.isfinite(c110)
        & np.isfinite(c001) & np.isfinite(c101) & np.isfinite(c011) & np.isfinite(c111)
    )
    pos_cnt = (
        (c000 > 0).astype(np.int8) + (c100 > 0).astype(np.int8)
        + (c010 > 0).astype(np.int8) + (c110 > 0).astype(np.int8)
        + (c001 > 0).astype(np.int8) + (c101 > 0).astype(np.int8)
        + (c011 > 0).astype(np.int8) + (c111 > 0).astype(np.int8)
    )
    active = valid & (pos_cnt > 0) & (pos_cnt < 8)
    ai, aj, ak = np.nonzero(active)
    if len(ai) == 0:
        return {
            "kind": "implicit3d",
            "verts": [],
            "quads": [],
            "zmin": -1.0,
            "zmax": 1.0,
            "latex": latex_str,
        }

    v_idx_grid = np.full((nx - 1, ny - 1, nz - 1), -1, dtype=np.int32)
    v_idx_grid[ai, aj, ak] = np.arange(len(ai), dtype=np.int32)

    edges = (
        ((0, 0, 0), (1, 0, 0)), ((0, 1, 0), (1, 1, 0)), ((0, 0, 1), (1, 0, 1)), ((0, 1, 1), (1, 1, 1)),
        ((0, 0, 0), (0, 1, 0)), ((1, 0, 0), (1, 1, 0)), ((0, 0, 1), (0, 1, 1)), ((1, 0, 1), (1, 1, 1)),
        ((0, 0, 0), (0, 0, 1)), ((1, 0, 0), (1, 0, 1)), ((0, 1, 0), (0, 1, 1)), ((1, 1, 0), (1, 1, 1)),
    )
    vx = np.zeros(len(ai), dtype=float)
    vy = np.zeros(len(ai), dtype=float)
    vz = np.zeros(len(ai), dtype=float)
    v_cnt = np.zeros(len(ai), dtype=float)

    for d0, d1 in edges:
        i0, j0, k0 = ai + d0[0], aj + d0[1], ak + d0[2]
        i1, j1, k1 = ai + d1[0], aj + d1[1], ak + d1[2]
        f0 = F[i0, j0, k0]
        f1 = F[i1, j1, k1]
        cross = (f0 > 0) != (f1 > 0)
        if not np.any(cross):
            continue
        denom = f0[cross] - f1[cross]
        tol = np.maximum(np.abs(f0[cross]), np.abs(f1[cross])) * 1e-12 + 1e-300
        good = np.abs(denom) > tol
        safe_d = np.where(good, denom, 1.0)
        t = np.clip(np.where(good, f0[cross] / safe_d, 0.5), 0.0, 1.0)
        vx[cross] += gx[i0[cross]] + t * (gx[i1[cross]] - gx[i0[cross]])
        vy[cross] += gy[j0[cross]] + t * (gy[j1[cross]] - gy[j0[cross]])
        vz[cross] += gz[k0[cross]] + t * (gz[k1[cross]] - gz[k0[cross]])
        v_cnt[cross] += 1.0

    safe_cnt = np.maximum(v_cnt, 1.0)
    vx /= safe_cnt
    vy /= safe_cnt
    vz /= safe_cnt

    verts = [[format_coord(x), format_coord(y), format_coord(z)] for x, y, z in zip(vx, vy, vz)]
    zmin = float(np.min(vz))
    zmax = float(np.max(vz))
    if abs(zmax - zmin) < 1e-9:
        zmin -= 1.0
        zmax += 1.0

    quads = []
    ex_cross = np.isfinite(F[:-1, 1:-1, 1:-1]) & np.isfinite(F[1:, 1:-1, 1:-1]) & ((F[:-1, 1:-1, 1:-1] > 0) != (F[1:, 1:-1, 1:-1] > 0))
    ei, ej, ek = np.nonzero(ex_cross)
    ej += 1
    ek += 1
    for i, j, k in zip(ei, ej, ek):
        q = (int(v_idx_grid[i, j - 1, k - 1]), int(v_idx_grid[i, j, k - 1]), int(v_idx_grid[i, j, k]), int(v_idx_grid[i, j - 1, k]))
        if q[0] >= 0 and q[1] >= 0 and q[2] >= 0 and q[3] >= 0:
            quads.append(list(q))

    ey_cross = np.isfinite(F[1:-1, :-1, 1:-1]) & np.isfinite(F[1:-1, 1:, 1:-1]) & ((F[1:-1, :-1, 1:-1] > 0) != (F[1:-1, 1:, 1:-1] > 0))
    ei, ej, ek = np.nonzero(ey_cross)
    ei += 1
    ek += 1
    for i, j, k in zip(ei, ej, ek):
        q = (int(v_idx_grid[i - 1, j, k - 1]), int(v_idx_grid[i - 1, j, k]), int(v_idx_grid[i, j, k]), int(v_idx_grid[i, j, k - 1]))
        if q[0] >= 0 and q[1] >= 0 and q[2] >= 0 and q[3] >= 0:
            quads.append(list(q))

    ez_cross = np.isfinite(F[1:-1, 1:-1, :-1]) & np.isfinite(F[1:-1, 1:-1, 1:]) & ((F[1:-1, 1:-1, :-1] > 0) != (F[1:-1, 1:-1, 1:] > 0))
    ei, ej, ek = np.nonzero(ez_cross)
    ei += 1
    ej += 1
    for i, j, k in zip(ei, ej, ek):
        q = (int(v_idx_grid[i - 1, j - 1, k]), int(v_idx_grid[i, j - 1, k]), int(v_idx_grid[i, j, k]), int(v_idx_grid[i - 1, j, k]))
        if q[0] >= 0 and q[1] >= 0 and q[2] >= 0 and q[3] >= 0:
            quads.append(list(q))

    return {
        "kind": "implicit3d",
        "verts": verts,
        "quads": quads,
        "zmin": format_coord(zmin),
        "zmax": format_coord(zmax),
        "latex": latex_str,
    }


def _try_extract_box_region(all_chains: list, finalize_fn, latex_str: str) -> dict | None:
    x_lo: float | None = None
    x_hi: float | None = None
    y_lo: float | None = None
    y_hi: float | None = None
    x_lo_s = False
    x_hi_s = False
    y_lo_s = False
    y_hi_s = False

    for lhs, op, rhs in all_chains:
        l_ev = _prepare_for_lambdify(finalize_fn(lhs))
        r_ev = _prepare_for_lambdify(finalize_fn(rhs))
        strict = op in ("<", ">")

        var_sym = None
        bound_val = None
        var_is_upper = False

        if l_ev in (X_SYM, Y_SYM) and not r_ev.free_symbols:
            var_sym = l_ev
            bound_val = float(r_ev.evalf())
            var_is_upper = op in (">", ">=")
        elif r_ev in (X_SYM, Y_SYM) and not l_ev.free_symbols:
            var_sym = r_ev
            bound_val = float(l_ev.evalf())
            var_is_upper = op in ("<", "<=")
        else:
            return None

        if bound_val is None or not math.isfinite(bound_val):
            return None

        if var_sym == X_SYM:
            if var_is_upper:
                if x_lo is None or bound_val > x_lo:
                    x_lo, x_lo_s = bound_val, strict
                elif bound_val == x_lo:
                    x_lo_s = x_lo_s or strict
            else:
                if x_hi is None or bound_val < x_hi:
                    x_hi, x_hi_s = bound_val, strict
                elif bound_val == x_hi:
                    x_hi_s = x_hi_s or strict
        else:
            if var_is_upper:
                if y_lo is None or bound_val > y_lo:
                    y_lo, y_lo_s = bound_val, strict
                elif bound_val == y_lo:
                    y_lo_s = y_lo_s or strict
            else:
                if y_hi is None or bound_val < y_hi:
                    y_hi, y_hi_s = bound_val, strict
                elif bound_val == y_hi:
                    y_hi_s = y_hi_s or strict

    if (x_lo is not None and x_hi is not None and x_lo > x_hi) or (y_lo is not None and y_hi is not None and y_lo > y_hi):
        return {"kind": "empty", "latex": latex_str}

    return {
        "kind": "rect_region",
        "x_lo": format_coord(x_lo) if x_lo is not None else None,
        "x_hi": format_coord(x_hi) if x_hi is not None else None,
        "y_lo": format_coord(y_lo) if y_lo is not None else None,
        "y_hi": format_coord(y_hi) if y_hi is not None else None,
        "strict_x": [x_lo_s, x_hi_s],
        "strict_y": [y_lo_s, y_hi_s],
        "latex": latex_str,
    }


def _eval_compound_inequality(
    main_chain: list,
    domain_chains: list,
    finalize_fn,
    vp: ViewportBounds,
    latex_str: str,
    num_registry: dict,
) -> dict:
    all_chains = main_chain + domain_chains
    box_res = _try_extract_box_region(all_chains, finalize_fn, latex_str)
    if box_res is not None:
        return box_res

    xmin, xmax, ymin, ymax = vp.xmin, vp.xmax, vp.ymin, vp.ymax
    mods = [num_registry, "numpy"]
    compiled = []
    for lhs, op, rhs in all_chains:
        diff_ev = _prepare_for_lambdify(finalize_fn(lhs - rhs))
        fn = sp.lambdify((X_SYM, Y_SYM), diff_ev, modules=mods)
        compiled.append((fn, op))

    mx, my = 160, 120
    sx = np.linspace(xmin, xmax, mx)
    sy = np.linspace(ymin, ymax, my)
    SX, SY = np.meshgrid(sx, sy)
    mask = np.ones(SX.shape, dtype=bool)
    for fn, op in compiled:
        SZ = _eval_numeric(fn, SX.shape, SX, SY)
        mask &= np.isfinite(SZ)
        if op == "<":
            mask &= SZ < 0.0
        elif op == "<=":
            mask &= SZ <= 1e-12
        elif op == ">":
            mask &= SZ > 0.0
        else:
            mask &= SZ >= -1e-12
    mask = np.flipud(mask)

    nx, ny = SAMPLING_CONFIG.implicit_nx, SAMPLING_CONFIG.implicit_ny
    gx = np.linspace(xmin, xmax, nx)
    gy = np.linspace(ymin, ymax, ny)
    X, Y = np.meshgrid(gx, gy)
    all_Z = [_eval_numeric(fn, X.shape, X, Y) for fn, _ in compiled]

    segs = []
    n_main = len(main_chain)
    for idx in range(n_main):
        Z_cur = all_Z[idx].copy()
        other_ok = np.ones(X.shape, dtype=bool)
        for j, (_fn, op) in enumerate(compiled):
            if j == idx:
                continue
            Zj = all_Z[j]
            other_ok &= np.isfinite(Zj)
            if op in ("<", "<="):
                other_ok &= Zj <= 1e-6
            else:
                other_ok &= Zj >= -1e-6
        Z_cur[~other_ok] = np.nan
        segs.extend(marching_squares(X, Y, Z_cur))

    any_strict = any(op in ("<", ">") for _l, op, _r in main_chain)
    return {
        "kind": "implicit",
        "segments": segs,
        "latex": latex_str,
        "strict": any_strict,
        "shade": {
            "w": mx,
            "h": my,
            "bounds": [format_coord(xmin), format_coord(xmax), format_coord(ymin), format_coord(ymax)],
            "bits": "".join("1" if b else "0" for b in mask.ravel()),
        },
    }


def _eval_regression(
    tbl_idx: int,
    rhs_raw: str,
    table_data: dict[int, tuple[np.ndarray, np.ndarray]],
    explicit_params: dict,
    named_funcs: dict,
    vp: ViewportBounds,
    num_registry: dict,
) -> tuple[dict, dict[str, float]]:
    data = table_data.get(tbl_idx)
    if data is None and table_data:
        data = next(iter(table_data.values()))
    if data is None or len(data[0]) < 2:
        return {
            "kind": "error",
            "error": f"Mind. 2 Datenpunkte in Tabelle {tbl_idx} benötigt",
            "latex": f"y_{{{tbl_idx}}} \\sim {rhs_raw}",
        }, {}

    tx, ty = data
    rhs_clean = preprocess_latex(rhs_raw)
    if not rhs_clean or rhs_clean == "__INCOMPLETE__":
        return {"kind": "incomplete", "latex": f"y_{{{tbl_idx}}} \\sim {rhs_raw}"}, {}

    model_sym = _parse_symbolic(rhs_clean, named_funcs)
    model_sym = _expand_named_funcs(model_sym, named_funcs, num_registry)
    model_sym = _substitute_params(model_sym, explicit_params)

    fit_syms = sorted(
        [s for s in model_sym.free_symbols if str(s) not in RESERVED_SYMS],
        key=lambda s: str(s),
    )
    if not fit_syms:
        return {
            "kind": "error",
            "error": "Keine freien Regressionsparameter (z.B. m, b) gefunden",
            "latex": f"y_{{{tbl_idx}}} \\sim {sp.latex(model_sym)}",
        }, {}

    fit_set = set(fit_syms)
    mods = [num_registry, "numpy"]
    cols = []
    for p in fit_syms:
        deriv = sp.diff(model_sym, p)
        if deriv.free_symbols & fit_set:
            return {
                "kind": "error",
                "error": "Parameter müssen linear im Modell auftreten (z.B. a*x^2 + b*x + c)",
                "latex": f"y_{{{tbl_idx}}} \\sim {sp.latex(model_sym)}",
            }, {}
        bfn = sp.lambdify(X_SYM, _prepare_for_lambdify(deriv), modules=mods)
        col = _eval_numeric(bfn, tx.shape, tx)
        cols.append(col)

    zero_subs = {p: sp.Integer(0) for p in fit_syms}
    offset_expr = model_sym.subs(zero_subs)
    off_fn = sp.lambdify(X_SYM, _prepare_for_lambdify(offset_expr), modules=mods)
    offset_vals = _eval_numeric(off_fn, tx.shape, tx)

    A = np.column_stack(cols)
    rhs_vec = ty - offset_vals
    valid = np.isfinite(rhs_vec) & np.all(np.isfinite(A), axis=1)
    if np.sum(valid) < len(fit_syms):
        return {
            "kind": "error",
            "error": "Zu wenige gültige Datenpunkte für die Parameteranzahl",
            "latex": f"y_{{{tbl_idx}}} \\sim {sp.latex(model_sym)}",
        }, {}

    A_v = A[valid]
    y_v = ty[valid]
    r_v = rhs_vec[valid]
    coeffs, *_ = np.linalg.lstsq(A_v, r_v, rcond=None)

    y_pred = A_v @ coeffs + offset_vals[valid]
    ss_res = float(np.sum((y_v - y_pred) ** 2))
    ss_tot = float(np.sum((y_v - np.mean(y_v)) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-15 else 1.0

    fitted_map = {str(p): float(c) for p, c in zip(fit_syms, coeffs)}
    fitted_expr = _substitute_params(model_sym, fitted_map)
    latex_str = f"y_{{{tbl_idx}}} \\sim {sp.latex(model_sym)}"

    curve_res, _ = _eval_explicit_curve(
        fitted_expr, vp, latex_str, num_registry, compute_kp=False
    )
    curve_res["kind"] = "regression"
    curve_res["params"] = {k: format_coord(v) for k, v in fitted_map.items()}
    curve_res["r2"] = round(float(r2), 5)
    return curve_res, fitted_map


def _eval_curve_family(
    expr,
    used_lists: list[str],
    list_params: dict[str, list[float]],
    finalize_fn,
    vp: ViewportBounds,
    latex_str: str,
    num_registry: dict,
    domain_chains: list,
) -> dict:
    n_curves = min(len(list_params[name]) for name in used_lists)
    n_curves = min(n_curves, SAMPLING_CONFIG.max_list_items)
    curves = []
    for idx in range(n_curves):
        step_subs = {name: list_params[name][idx] for name in used_lists}
        ev = _substitute_params(finalize_fn(expr), step_subs)
        dom_fn = None
        dom_bounds = None
        if domain_chains:
            dom_fn, dom_bounds = _build_domain_mask_fn(
                domain_chains,
                lambda e, ss=step_subs: _substitute_params(finalize_fn(e), ss),
                num_registry,
            )
        sub_res, _ = _eval_explicit_curve(
            ev, vp, latex_str, num_registry,
            domain_fn=dom_fn, domain_bounds=dom_bounds, compute_kp=False,
        )
        curves.append(sub_res["points"])

    return {
        "kind": "curve_family",
        "curves": curves,
        "count": len(curves),
        "latex": latex_str,
    }


def _eval_surface_3d_family(
    rhs_expr,
    used_lists: list[str],
    list_params: dict[str, list[float]],
    finalize_fn,
    vp: ViewportBounds,
    latex_str: str,
    num_registry: dict,
    domain_chains: list,
) -> dict:
    n_items = min(len(list_params[name]) for name in used_lists)
    n_items = min(n_items, SAMPLING_CONFIG.max_list_items)
    verts: list = []
    quads: list = []
    all_zs: list[float] = []

    for idx in range(n_items):
        ss = {name: list_params[name][idx] for name in used_lists}
        ev = _substitute_params(finalize_fn(rhs_expr), ss)
        dom_fn = None
        if domain_chains:
            dom_fn, _ = _build_domain_mask_fn(
                domain_chains,
                lambda e, ss=ss: _substitute_params(finalize_fn(e), ss),
                num_registry,
            )
        sub = _eval_surface_3d(ev, vp, latex_str, num_registry, domain_fn=dom_fn)
        gx, gy, gz = sub["gx"], sub["gy"], sub["gz"]
        ny, nx = len(gy), len(gx)
        grid_idx = [[-1] * nx for _ in range(ny)]
        for r in range(ny):
            for c in range(nx):
                zv = gz[r][c]
                if zv is not None:
                    grid_idx[r][c] = len(verts)
                    verts.append([gx[c], gy[r], zv])
                    all_zs.append(zv)
        for r in range(ny - 1):
            for c in range(nx - 1):
                i00, i10, i11, i01 = grid_idx[r][c], grid_idx[r][c + 1], grid_idx[r + 1][c + 1], grid_idx[r + 1][c]
                if i00 >= 0 and i10 >= 0 and i11 >= 0 and i01 >= 0:
                    quads.append([i00, i10, i11, i01])

    zmin = min(all_zs) if all_zs else -1.0
    zmax = max(all_zs) if all_zs else 1.0
    if abs(zmax - zmin) < 1e-9:
        zmin -= 1.0
        zmax += 1.0
    return {
        "kind": "implicit3d",
        "verts": verts,
        "quads": quads,
        "zmin": format_coord(zmin),
        "zmax": format_coord(zmax),
        "latex": latex_str,
    }


def _eval_implicit_family(
    diff_expr,
    used_lists: list[str],
    list_params: dict[str, list[float]],
    finalize_fn,
    vp: ViewportBounds,
    latex_str: str,
    num_registry: dict,
    domain_chains: list,
    ineq_op: str | None = None,
    strict: bool = False,
) -> dict:
    n_items = min(len(list_params[name]) for name in used_lists)
    n_items = min(n_items, SAMPLING_CONFIG.max_list_items)

    all_segs: list = []
    combined_mask: np.ndarray | None = None
    shade_meta = None

    for idx in range(n_items):
        step_subs = {name: list_params[name][idx] for name in used_lists}
        ev = _substitute_params(finalize_fn(diff_expr), step_subs)
        dom_fn = None
        if domain_chains:
            dom_fn, _ = _build_domain_mask_fn(
                domain_chains,
                lambda e, ss=step_subs: _substitute_params(finalize_fn(e), ss),
                num_registry,
            )
        sub_res = _eval_implicit(
            ev, vp, latex_str, num_registry,
            ineq_op=ineq_op, strict=strict, domain_fn=dom_fn,
        )
        all_segs.extend(sub_res.get("segments", []))
        if "shade" in sub_res:
            sh = sub_res["shade"]
            bits_arr = np.frombuffer(sh["bits"].encode("ascii"), dtype=np.uint8) == ord("1")
            if combined_mask is None:
                combined_mask = bits_arr.copy()
                shade_meta = (sh["w"], sh["h"], sh["bounds"])
            else:
                combined_mask |= bits_arr

    res: dict = {
        "kind": "implicit",
        "segments": all_segs,
        "latex": latex_str,
        "strict": strict,
    }
    if combined_mask is not None and shade_meta is not None:
        res["shade"] = {
            "w": shade_meta[0],
            "h": shade_meta[1],
            "bounds": shade_meta[2],
            "bits": "".join("1" if b else "0" for b in combined_mask),
        }
    return res


def _eval_flat_region_3d(
    diff_exprs: list,
    ineq_op: str,
    z_val: float,
    vp: ViewportBounds,
    latex_str: str,
    num_registry: dict,
    domain_fns: list | None = None,
) -> dict:
    mods = [num_registry, "numpy"]
    fns = [sp.lambdify((X_SYM, Y_SYM), _prepare_for_lambdify(de), modules=mods) for de in diff_exprs]

    half = min(max(0.5 * min(vp.x_span, vp.y_span), 1e-4), 1e6)
    nx = ny = 96
    gx = np.linspace(vp.cx - half, vp.cx + half, nx)
    gy = np.linspace(vp.cy - half, vp.cy + half, ny)
    X2, Y2 = np.meshgrid(gx, gy, indexing="ij")

    mask = np.zeros(X2.shape, dtype=bool)
    for idx, fn in enumerate(fns):
        Z2 = _eval_numeric(fn, X2.shape, X2, Y2)
        if ineq_op == "<":
            m = Z2 < 0.0
        elif ineq_op == "<=":
            m = Z2 <= 1e-9
        elif ineq_op == ">":
            m = Z2 > 0.0
        else:
            m = Z2 >= -1e-9
        if domain_fns and domain_fns[idx] is not None:
            m &= domain_fns[idx](X2, Y2)
        mask |= m

    cell_cnt = (
        mask[:-1, :-1].astype(np.int8)
        + mask[1:, :-1].astype(np.int8)
        + mask[:-1, 1:].astype(np.int8)
        + mask[1:, 1:].astype(np.int8)
    )
    active_cells = cell_cnt >= 2
    ci, cj = np.nonzero(active_cells)

    if len(ci) == 0:
        return {
            "kind": "implicit3d",
            "verts": [],
            "quads": [],
            "zmin": format_coord(z_val - 1.0),
            "zmax": format_coord(z_val + 1.0),
            "latex": latex_str,
        }

    v_map: dict[tuple[int, int], int] = {}
    verts: list = []
    quads: list = []
    zf = format_coord(z_val)

    def _get_v(ii: int, jj: int) -> int:
        key = (ii, jj)
        idx = v_map.get(key)
        if idx is None:
            idx = len(verts)
            v_map[key] = idx
            verts.append([format_coord(gx[ii]), format_coord(gy[jj]), zf])
        return idx

    for i, j in zip(ci, cj):
        ii, jj = int(i), int(j)
        quads.append([_get_v(ii, jj), _get_v(ii + 1, jj), _get_v(ii + 1, jj + 1), _get_v(ii, jj + 1)])

    return {
        "kind": "implicit3d",
        "is_flat": True,
        "z_plane": zf,
        "verts": verts,
        "quads": quads,
        "zmin": format_coord(z_val - 0.5),
        "zmax": format_coord(z_val + 0.5),
        "latex": latex_str,
    }


def evaluate_all_expressions(items: list, explicit_params: dict, auto_params: dict, bounds: dict, settings: dict) -> list:
    auto_sliders_on = bool(settings.get("auto_sliders", True))
    show_key_points = bool(settings.get("show_key_points", True))
    vp = bounds if isinstance(bounds, ViewportBounds) else ViewportBounds.from_dict(bounds)

    table_data: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    table_counter = 0
    prepped_list = []

    for item in items:
        itype = item.get("type", "expr")
        if itype == "table":
            table_counter += 1
            rows = item.get("rows") or []
            xs_list, ys_list = [], []
            for row in rows:
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                try:
                    xv = float(row[0])
                    yv = float(row[1])
                    if math.isfinite(xv) and math.isfinite(yv):
                        xs_list.append(xv)
                        ys_list.append(yv)
                except (TypeError, ValueError):
                    pass
            if xs_list:
                table_data[table_counter] = (np.array(xs_list, dtype=float), np.array(ys_list, dtype=float))
            prepped_list.append((item, "", "", "", [], table_counter))
            continue

        if itype in ("note", "folder"):
            prepped_list.append((item, "", "", "", [], 0))
            continue

        raw = item.get("raw", "")
        main_raw, domain_strs = extract_domain_restrictions(raw)
        cleaned = preprocess_latex(main_raw)
        prepped_list.append((item, raw, main_raw, cleaned, domain_strs, 0))

    resolved_explicit = dict(explicit_params)
    list_params: dict[str, list[float]] = {}

    for item, raw, main_raw, cleaned, domain_strs, _tidx in prepped_list:
        if item.get("type", "expr") != "expr" or not raw.strip() or domain_strs:
            continue

        parsed_list = parse_list_definition(main_raw, max_items=SAMPLING_CONFIG.max_list_items)
        if parsed_list is not None:
            lname, lvals = parsed_list
            list_params[lname] = lvals
            resolved_explicit.pop(lname, None)
            continue

        if not cleaned or cleaned == "__INCOMPLETE__":
            continue

        m_param = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*=\s*(.+)$", cleaned)
        if m_param:
            lhs_name, rhs_str = m_param.group(1), m_param.group(2)
            if (
                _is_valid_slider_name(lhs_name)
                and not any(op in rhs_str for op in ("<", ">", "="))
            ):
                try:
                    rhs_e = _parse_symbolic(rhs_str, {})
                    rhs_e = _substitute_params(rhs_e, resolved_explicit)
                    if not rhs_e.free_symbols:
                        val = float(_prepare_for_lambdify(rhs_e).evalf())
                        if math.isfinite(val):
                            resolved_explicit[lhs_name] = val
                except Exception:
                    pass

    all_values = dict(auto_params)
    all_values.update(resolved_explicit)

    named_funcs = {}
    for item, _raw, main_raw, cleaned, _domain_strs, _tidx in prepped_list:
        if item.get("type", "expr") != "expr" or not cleaned or cleaned == "__INCOMPLETE__":
            continue
        if "=" in main_raw and not any(op in main_raw for op in ("<=", ">=", "<", ">", "\\le", "\\ge")):
            lhs_raw, rhs_raw = main_raw.split("=", 1)
            lhs_clean = preprocess_latex(lhs_raw)
            m_fn = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*\(\s*([a-zA-Z])\s*\)$", lhs_clean.strip())
            if m_fn:
                fn_name, arg_name = m_fn.group(1), m_fn.group(2)
                if fn_name not in BUILTIN_FUNC_NAMES and fn_name not in RESERVED_SYMS:
                    try:
                        arg_sym = sp.Symbol(arg_name, real=True)
                        pw = parse_piecewise_rhs(rhs_raw, named_funcs)
                        if pw is not None:
                            rhs_sym = pw
                        else:
                            rhs_sym = _parse_symbolic(preprocess_latex(rhs_raw), named_funcs)
                        rhs_free = [
                            str(s)
                            for s in rhs_sym.free_symbols
                            if str(s) not in (_ALWAYS_CONST_SYMS | {"x", "y", "z"}) and str(s) != arg_name and str(s) not in list_params
                        ]
                        sub_map = dict(all_values)
                        if auto_sliders_on:
                            for vname in rhs_free:
                                if vname not in sub_map:
                                    sub_map[vname] = 1.0
                        rhs_eval = _substitute_params(rhs_sym, sub_map)
                        named_funcs[fn_name] = {
                            "var": arg_sym,
                            "expr": rhs_eval,
                        }
                    except Exception:
                        pass

    results = []
    explicit_callables = []

    for item, raw_expr, main_raw, cleaned, domain_strs, tidx in prepped_list:
        itype = item.get("type", "expr")
        if itype == "note":
            results.append({"id": item["id"], "kind": "note"})
            continue
        if itype == "folder":
            results.append({"id": item["id"], "kind": "folder"})
            continue
        if itype == "table":
            pts = []
            if tidx in table_data:
                tx, ty = table_data[tidx]
                pts = [[format_coord(x), format_coord(y)] for x, y in zip(tx, ty)]
            results.append({"id": item["id"], "kind": "table_points", "table_index": tidx, "points": pts})
            continue

        res, eval_meta, fitted_params = evaluate_single(
            raw_expr=raw_expr,
            main_raw=main_raw,
            cleaned=cleaned,
            domain_strs=domain_strs,
            explicit_params=resolved_explicit,
            auto_params=auto_params,
            list_params=list_params,
            table_data=table_data,
            named_funcs=named_funcs,
            vp=vp,
            auto_sliders_on=auto_sliders_on,
            table_xs=item.get("table_xs"),
            compute_kp=show_key_points and bool(item.get("visible", True)),
        )
        res["id"] = item["id"]
        results.append(res)
        if fitted_params:
            resolved_explicit.update(fitted_params)
        if eval_meta is not None and bool(item.get("visible", True)):
            eval_meta["id"] = item["id"]
            eval_meta["res"] = res
            explicit_callables.append(eval_meta)

    if show_key_points and len(explicit_callables) >= 2:
        n_c = len(explicit_callables)
        for i in range(n_c):
            for j in range(i + 1, n_c):
                inter_pts = _compute_intersections(explicit_callables[i], explicit_callables[j], vp)
                if inter_pts:
                    for target in (explicit_callables[i]["res"], explicit_callables[j]["res"]):
                        existing = target.get("key_points", [])
                        merged = _dedup_keypoints(
                            existing + inter_pts,
                            vp.x_span * 2e-3,
                            vp.y_span * 2e-3,
                            SAMPLING_CONFIG.max_key_points_per_type,
                        )
                        target["key_points"] = merged

    return results


def evaluate_single(
    raw_expr: str,
    main_raw: str,
    cleaned: str,
    domain_strs: list[str],
    explicit_params: dict,
    auto_params: dict,
    list_params: dict[str, list[float]],
    table_data: dict[int, tuple[np.ndarray, np.ndarray]],
    named_funcs: dict,
    vp: ViewportBounds,
    auto_sliders_on: bool,
    table_xs: list | None = None,
    compute_kp: bool = True,
) -> tuple[dict, dict | None, dict[str, float] | None]:
    if not raw_expr.strip():
        return {"kind": "empty", "latex": ""}, None, None

    x_span, y_span = vp.x_span, vp.y_span
    num_registry = dict(BASE_NUMPY_MAP)

    try:
        if not domain_strs:
            parsed_list = parse_list_definition(main_raw, max_items=SAMPLING_CONFIG.max_list_items)
            if parsed_list is not None:
                lname, lvals = parsed_list
                preview = ", ".join(f"{v:g}" for v in lvals[:6])
                if len(lvals) > 6:
                    preview += f", \\dots, {lvals[-1]:g}"
                return {
                    "kind": "list",
                    "name": lname,
                    "values": lvals,
                    "count": len(lvals),
                    "latex": f"{sp.latex(sp.Symbol(lname))} = \\left[{preview}\\right]",
                }, None, None

        reg_parsed = parse_regression_expr(main_raw)
        if reg_parsed is not None:
            tbl_idx, rhs_raw = reg_parsed
            reg_res, fitted = _eval_regression(
                tbl_idx, rhs_raw, table_data, explicit_params, named_funcs, vp, num_registry
            )
            return reg_res, None, fitted

        inline_lists_early: dict[str, list[float]] = {}
        if "[" in main_raw:
            main_raw_il, inline_lists_early = extract_inline_lists(main_raw, max_items=SAMPLING_CONFIG.max_list_items)
            if inline_lists_early:
                main_raw = main_raw_il
                cleaned = preprocess_latex(main_raw)
        eff_list_params = {**list_params, **inline_lists_early} if inline_lists_early else list_params

        ode_rhs = parse_ode_equation(main_raw)
        if ode_rhs is not None:
            rhs_clean = preprocess_latex(ode_rhs)
            if not rhs_clean or rhs_clean == "__INCOMPLETE__":
                return {"kind": "incomplete", "latex": raw_expr}, None, None
            rhs_sym = _parse_symbolic(rhs_clean, named_funcs)
            rhs_exp = _expand_named_funcs(rhs_sym, named_funcs, num_registry)
            dom_chains = parse_domain_conditions(domain_strs, named_funcs) if domain_strs else []
            dom_exprs = [e for l, _o, r in dom_chains for e in (l, r)]
            dom_tex = ("\\; " + _format_domain_latex(dom_chains)) if dom_chains else ""
            latex_str = f"y' = {sp.latex(rhs_sym)}" + dom_tex
            auto_vars = _detect_auto_vars([rhs_exp] + dom_exprs, explicit_params, named_funcs, eff_list_params, bound_vars={"x", "y"})
            if auto_vars and not auto_sliders_on:
                return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None
            sub_map = dict(auto_params)
            if auto_sliders_on:
                for v in auto_vars:
                    sub_map.setdefault(v, 1.0)
            sub_map.update(explicit_params)
            rhs_ev = _substitute_params(rhs_exp, sub_map)
            dom_fn, _ = _build_domain_mask_fn(dom_chains, lambda e: _substitute_params(_expand_named_funcs(e, named_funcs, num_registry), sub_map), num_registry)
            sf_res = _eval_slope_field(rhs_ev, vp, latex_str, num_registry, domain_fn=dom_fn)
            sf_res["auto_vars"] = auto_vars
            return sf_res, None, None

        surf_rhs = parse_surface_3d(main_raw)
        if surf_rhs is not None:
            rhs_clean = preprocess_latex(surf_rhs)
            if not rhs_clean or rhs_clean == "__INCOMPLETE__":
                return {"kind": "incomplete", "latex": raw_expr}, None, None
            rhs_sym = _parse_symbolic(rhs_clean, named_funcs)
            rhs_exp = _expand_named_funcs(rhs_sym, named_funcs, num_registry)
            dom_chains = parse_domain_conditions(domain_strs, named_funcs) if domain_strs else []
            dom_exprs = [e for l, _o, r in dom_chains for e in (l, r)]
            dom_tex = ("\\; " + _format_domain_latex(dom_chains)) if dom_chains else ""
            latex_str = f"z = {sp.latex(rhs_sym)}" + dom_tex
            auto_vars = _detect_auto_vars([rhs_exp] + dom_exprs, explicit_params, named_funcs, eff_list_params, bound_vars={"x", "y", "z"})
            if auto_vars and not auto_sliders_on:
                return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None
            sub_map = dict(auto_params)
            if auto_sliders_on:
                for v in auto_vars:
                    sub_map.setdefault(v, 1.0)
            sub_map.update(explicit_params)
            used_lists = _detect_used_lists([rhs_exp] + dom_exprs, eff_list_params)
            if used_lists:
                s3_res = _eval_surface_3d_family(
                    rhs_exp, used_lists, eff_list_params,
                    lambda e: _substitute_params(_expand_named_funcs(e, named_funcs, num_registry), sub_map),
                    vp, latex_str, num_registry, dom_chains,
                )
            else:
                rhs_ev = _substitute_params(rhs_exp, sub_map)
                dom_fn, _ = _build_domain_mask_fn(dom_chains, lambda e: _substitute_params(_expand_named_funcs(e, named_funcs, num_registry), sub_map), num_registry)
                s3_res = _eval_surface_3d(rhs_ev, vp, latex_str, num_registry, domain_fn=dom_fn)
            s3_res["auto_vars"] = auto_vars
            return s3_res, None, None


        if not cleaned:
            return {"kind": "empty", "latex": ""}, None, None
        if cleaned == "__INCOMPLETE__":
            return {"kind": "incomplete", "latex": raw_expr}, None, None

        z_plane_expr, filtered_domain_strs = extract_z_plane_restriction(domain_strs, named_funcs)
        domain_chains = parse_domain_conditions(filtered_domain_strs, named_funcs) if filtered_domain_strs else []
        domain_exprs = [e for l, _o, r in domain_chains for e in (l, r)]
        if z_plane_expr is not None:
            domain_exprs.append(z_plane_expr)
        domain_tex = ("\\; " + _format_domain_latex(domain_chains)) if domain_chains else ""
        if z_plane_expr is not None:
            domain_tex += rf"\; \left\{{z = {sp.latex(z_plane_expr)}\right\}}"

        def _finalize(expr_obj, extra_auto=None):
            expanded = _expand_named_funcs(expr_obj, named_funcs, num_registry)
            sub_map = dict(auto_params)
            if auto_sliders_on and extra_auto:
                for v in extra_auto:
                    if v not in sub_map:
                        sub_map[v] = 1.0
            sub_map.update(explicit_params)
            return _substitute_params(expanded, sub_map)

        if not domain_chains:
            m_param = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*=\s*(.+)$", cleaned)
            if m_param:
                lhs_name, rhs_str = m_param.group(1), m_param.group(2)
                if (
                    _is_valid_slider_name(lhs_name)
                    and not any(op in rhs_str for op in ("<", ">", "="))
                ):
                    rhs_sym = _parse_symbolic(rhs_str, named_funcs)
                    rhs_ev = _finalize(rhs_sym)
                    if not rhs_ev.free_symbols:
                        val = float(_prepare_for_lambdify(rhs_ev).evalf())
                        sym_tex = sp.latex(sp.Symbol(lhs_name))
                        return {
                            "kind": "slider",
                            "name": lhs_name,
                            "value": val,
                            "latex": f"{sym_tex} = {val:g}",
                        }, None, None

        tup = split_top_level_tuple(cleaned)
        if tup is not None and len(tup) == 3:
            ex_x = _parse_symbolic(tup[0], named_funcs)
            ex_y = _parse_symbolic(tup[1], named_funcs)
            ex_z = _parse_symbolic(tup[2], named_funcs)
            latex_str = rf"\left({sp.latex(ex_x)},\; {sp.latex(ex_y)},\; {sp.latex(ex_z)}\right)" + domain_tex
            all_free = ex_x.free_symbols | ex_y.free_symbols | ex_z.free_symbols
            is_uv = bool({U_SYM, V_SYM} & all_free)
            is_t = T_SYM in all_free

            extra_reserved = {"u", "v"} if is_uv else set()
            auto_vars = [
                v for v in _detect_auto_vars([ex_x, ex_y, ex_z] + domain_exprs, explicit_params, named_funcs, eff_list_params)
                if v not in extra_reserved
            ]
            if auto_vars and not auto_sliders_on:
                return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None

            ex_x_ev = _finalize(ex_x, auto_vars)
            ex_y_ev = _finalize(ex_y, auto_vars)
            ex_z_ev = _finalize(ex_z, auto_vars)

            if is_uv:
                res = _eval_parametric_surface_3d(ex_x_ev, ex_y_ev, ex_z_ev, latex_str, num_registry)
                res["auto_vars"] = auto_vars
                return res, None, None

            mods = [num_registry, "numpy"]
            if is_t:
                fx = sp.lambdify(T_SYM, _prepare_for_lambdify(ex_x_ev), modules=mods)
                fy = sp.lambdify(T_SYM, _prepare_for_lambdify(ex_y_ev), modules=mods)
                fz = sp.lambdify(T_SYM, _prepare_for_lambdify(ex_z_ev), modules=mods)
                ts = np.linspace(0.0, 4.0 * np.pi, 600)
                xs = _eval_numeric(fx, ts.shape, ts)
                ys = _eval_numeric(fy, ts.shape, ts)
                zs = _eval_numeric(fz, ts.shape, ts)
                pts3d = [
                    [format_coord(x), format_coord(y), format_coord(z)]
                    if (math.isfinite(x) and math.isfinite(y) and math.isfinite(z))
                    else None
                    for x, y, z in zip(xs, ys, zs)
                ]
                return {"kind": "curve3d", "points": pts3d, "latex": latex_str, "auto_vars": auto_vars}, None, None

            if not (ex_x_ev.free_symbols | ex_y_ev.free_symbols | ex_z_ev.free_symbols):
                fx = sp.lambdify((), _prepare_for_lambdify(ex_x_ev), modules=mods)
                fy = sp.lambdify((), _prepare_for_lambdify(ex_y_ev), modules=mods)
                fz = sp.lambdify((), _prepare_for_lambdify(ex_z_ev), modules=mods)
                px = float(_eval_numeric(fx, (1,))[0])
                py = float(_eval_numeric(fy, (1,))[0])
                pz = float(_eval_numeric(fz, (1,))[0])
                if math.isfinite(px) and math.isfinite(py) and math.isfinite(pz):
                    return {
                        "kind": "point3d",
                        "point": [format_coord(px), format_coord(py), format_coord(pz)],
                        "latex": latex_str,
                        "auto_vars": auto_vars,
                    }, None, None

        pair = split_top_level_comma(cleaned)
        if pair is not None:
            ex_x = _parse_symbolic(pair[0], named_funcs)
            ex_y = _parse_symbolic(pair[1], named_funcs)
            ex_x_exp = _expand_named_funcs(ex_x, named_funcs, num_registry)
            ex_y_exp = _expand_named_funcs(ex_y, named_funcs, num_registry)
            latex_str = rf"\left({sp.latex(ex_x)},\; {sp.latex(ex_y)}\right)" + domain_tex
            has_t = T_SYM in (ex_x_exp.free_symbols | ex_y_exp.free_symbols) and "t" not in explicit_params and "t" not in eff_list_params
            bvars = {"t"} if has_t else set()
            auto_vars = _detect_auto_vars([ex_x_exp, ex_y_exp] + domain_exprs, explicit_params, named_funcs, eff_list_params, bound_vars=bvars)
            if auto_vars and not auto_sliders_on:
                return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None

            used_lists = _detect_used_lists([ex_x_exp, ex_y_exp] + domain_exprs, eff_list_params)
            mods = [num_registry, "numpy"]

            if used_lists and not has_t:
                n_pts = min(len(eff_list_params[nm]) for nm in used_lists)
                pts_out = []
                for idx in range(min(n_pts, SAMPLING_CONFIG.max_list_items)):
                    ss = {nm: eff_list_params[nm][idx] for nm in used_lists}
                    px_e = _prepare_for_lambdify(_substitute_params(_finalize(ex_x_exp, auto_vars), ss))
                    py_e = _prepare_for_lambdify(_substitute_params(_finalize(ex_y_exp, auto_vars), ss))
                    fx = sp.lambdify((), px_e, modules=mods)
                    fy = sp.lambdify((), py_e, modules=mods)
                    px = float(_eval_numeric(fx, (1,))[0])
                    py = float(_eval_numeric(fy, (1,))[0])
                    if math.isfinite(px) and math.isfinite(py):
                        pts_out.append([format_coord(px), format_coord(py)])
                return {"kind": "table_points", "points": pts_out, "latex": latex_str, "auto_vars": auto_vars}, None, None

            ex_x_ev = _prepare_for_lambdify(_finalize(ex_x_exp, auto_vars))
            ex_y_ev = _prepare_for_lambdify(_finalize(ex_y_exp, auto_vars))

            if not (ex_x_ev.free_symbols | ex_y_ev.free_symbols):
                fx = sp.lambdify((), ex_x_ev, modules=mods)
                fy = sp.lambdify((), ex_y_ev, modules=mods)
                px = float(_eval_numeric(fx, (1,))[0])
                py = float(_eval_numeric(fy, (1,))[0])
                if math.isfinite(px) and math.isfinite(py):
                    return {
                        "kind": "point",
                        "point": [format_coord(px), format_coord(py)],
                        "latex": latex_str,
                        "auto_vars": auto_vars,
                    }, None, None
                return {"kind": "empty", "latex": latex_str, "auto_vars": auto_vars}, None, None

            fx = sp.lambdify(T_SYM, ex_x_ev, modules=mods)
            fy = sp.lambdify(T_SYM, ex_y_ev, modules=mods)
            t_lo, t_hi = _extract_param_bounds(domain_chains, T_SYM, lambda e: _finalize(e, auto_vars), 0.0, 2.0 * np.pi)
            ts = np.linspace(t_lo, t_hi, SAMPLING_CONFIG.parametric_samples)
            xs = _eval_numeric(fx, ts.shape, ts)
            ys = _eval_numeric(fy, ts.shape, ts)
            if domain_chains:
                dom_fn, _ = _build_domain_mask_fn(domain_chains, lambda e: _finalize(e, auto_vars), num_registry)
                if dom_fn is not None:
                    mask = dom_fn(xs, ys, t_arr=ts)
                    xs[~mask] = np.nan
                    ys[~mask] = np.nan
            pts = _pack_parametric_polyline(xs, ys, x_span, y_span)
            return {"kind": "curve", "points": pts, "latex": latex_str, "auto_vars": auto_vars}, None, None

        if "=" in main_raw and ":" in main_raw:
            lhs_raw, rhs_raw = main_raw.split("=", 1)
            pw = parse_piecewise_rhs(rhs_raw, named_funcs)
            if pw is not None:
                lhs_clean = preprocess_latex(lhs_raw).strip()
                m_fn = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*\(\s*([a-zA-Z])\s*\)$", lhs_clean)
                arg_name = m_fn.group(2) if m_fn else "x"
                latex_str = f"{lhs_clean} = {sp.latex(pw)}" + domain_tex
                auto_vars = [
                    v for v in _detect_auto_vars([pw] + domain_exprs, explicit_params, named_funcs, eff_list_params) if v != arg_name
                ]
                if auto_vars and not auto_sliders_on:
                    return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None
                ev_expr = _finalize(pw, auto_vars)
                if arg_name != "x":
                    ev_expr = ev_expr.subs(sp.Symbol(arg_name, real=True), X_SYM)
                dom_fn, dom_bounds = _build_domain_mask_fn(domain_chains, lambda e: _finalize(e, auto_vars), num_registry)
                res, meta = _eval_explicit_curve(
                    ev_expr, vp, latex_str, num_registry,
                    domain_fn=dom_fn, domain_bounds=dom_bounds,
                    table_xs=table_xs, compute_kp=compute_kp,
                )
                res["auto_vars"] = auto_vars
                return res, meta, None

        if any(op in cleaned for op in ("<=", ">=", "<", ">")):
            main_chain = parse_single_condition_chain(main_raw, named_funcs)
            if main_chain:
                op_map = {"<=": r"\le", ">=": r"\ge", "<": "<", ">": ">"}
                chain_tex_parts = [sp.latex(main_chain[0][0])]
                for _l, o, r in main_chain:
                    chain_tex_parts.append(op_map[o])
                    chain_tex_parts.append(sp.latex(r))
                latex_str = " ".join(chain_tex_parts) + domain_tex

                main_exprs = [e for l, _o, r in main_chain for e in (l, r)]
                auto_vars = _detect_auto_vars(main_exprs + domain_exprs, explicit_params, named_funcs, eff_list_params)
                if auto_vars and not auto_sliders_on:
                    return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None

                box_res = _try_extract_box_region(
                    main_chain + domain_chains,
                    lambda e: _finalize(e, auto_vars),
                    latex_str,
                )
                if box_res is not None:
                    box_res["auto_vars"] = auto_vars
                    return box_res, None, None

                if len(main_chain) >= 2:
                    res = _eval_compound_inequality(
                        main_chain, domain_chains,
                        lambda e: _finalize(e, auto_vars),
                        vp, latex_str, num_registry,
                    )
                    res["auto_vars"] = auto_vars
                    return res, None, None

                lhs_e, ineq_op, rhs_e = main_chain[0]
                lhs_exp = _expand_named_funcs(lhs_e, named_funcs, num_registry)
                rhs_exp = _expand_named_funcs(rhs_e, named_funcs, num_registry)
                used_lists_ineq = _detect_used_lists([lhs_exp, rhs_exp] + domain_exprs, eff_list_params)
                dom_fn, dom_bounds = _build_domain_mask_fn(domain_chains, lambda e: _finalize(e, auto_vars), num_registry)
                strict = ineq_op in ("<", ">")
                if not used_lists_ineq and z_plane_expr is None and lhs_e == Y_SYM and Y_SYM not in rhs_exp.free_symbols:
                    direction = "above" if ineq_op in (">", ">=") else "below"
                    res, _ = _eval_explicit_curve(
                        _finalize(rhs_e, auto_vars), vp, latex_str, num_registry,
                        ineq=direction, strict=strict, domain_fn=dom_fn, domain_bounds=dom_bounds,
                        compute_kp=False,
                    )
                    res["auto_vars"] = auto_vars
                    return res, None, None
                if not used_lists_ineq and z_plane_expr is None and rhs_e == Y_SYM and Y_SYM not in lhs_exp.free_symbols:
                    direction = "below" if ineq_op in (">", ">=") else "above"
                    res, _ = _eval_explicit_curve(
                        _finalize(lhs_e, auto_vars), vp, latex_str, num_registry,
                        ineq=direction, strict=strict, domain_fn=dom_fn, domain_bounds=dom_bounds,
                        compute_kp=False,
                    )
                    res["auto_vars"] = auto_vars
                    return res, None, None

                used_lists = _detect_used_lists([lhs_e, rhs_e] + domain_exprs, eff_list_params)

                if z_plane_expr is not None:
                    z_ev = _prepare_for_lambdify(_finalize(z_plane_expr, auto_vars))
                    if not z_ev.free_symbols:
                        z_val = float(z_ev.evalf())
                        if math.isfinite(z_val):
                            diff_base = lhs_e - rhs_e
                            if used_lists:
                                n_it = min(len(eff_list_params[nm]) for nm in used_lists)
                                diff_list = []
                                dom_list = []
                                for k_i in range(min(n_it, SAMPLING_CONFIG.max_list_items)):
                                    ss = {nm: eff_list_params[nm][k_i] for nm in used_lists}
                                    diff_list.append(_substitute_params(_finalize(diff_base, auto_vars), ss))
                                    if domain_chains:
                                        df, _ = _build_domain_mask_fn(domain_chains, lambda e, ss=ss: _substitute_params(_finalize(e, auto_vars), ss), num_registry)
                                        dom_list.append(df)
                                    else:
                                        dom_list.append(None)
                                res = _eval_flat_region_3d(diff_list, ineq_op, z_val, vp, latex_str, num_registry, dom_list)
                            else:
                                res = _eval_flat_region_3d([_finalize(diff_base, auto_vars)], ineq_op, z_val, vp, latex_str, num_registry, [dom_fn])
                            res["auto_vars"] = auto_vars
                            return res, None, None

                if used_lists:
                    res = _eval_implicit_family(
                        lhs_e - rhs_e, used_lists, eff_list_params,
                        lambda e: _finalize(e, auto_vars),
                        vp, latex_str, num_registry, domain_chains,
                        ineq_op=ineq_op, strict=strict,
                    )
                    res["auto_vars"] = auto_vars
                    return res, None, None

                diff_ev = _finalize(lhs_e - rhs_e, auto_vars)
                res = _eval_implicit(
                    diff_ev, vp, latex_str, num_registry,
                    ineq_op=ineq_op, strict=strict, domain_fn=dom_fn,
                )
                res["auto_vars"] = auto_vars
                return res, None, None

        if "=" in cleaned:
            lhs_s, rhs_s = cleaned.split("=", 1)
            lhs_strip = lhs_s.strip()

            m_fn = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*\(\s*([a-zA-Z])\s*\)$", lhs_strip)
            if m_fn and m_fn.group(1) not in BUILTIN_FUNC_NAMES and m_fn.group(1) not in RESERVED_SYMS:
                fn_name, arg_name = m_fn.group(1), m_fn.group(2)
                rhs_e = _parse_symbolic(rhs_s, named_funcs)
                latex_str = f"{fn_name}({arg_name}) = {sp.latex(rhs_e)}" + domain_tex
                auto_vars = [
                    v for v in _detect_auto_vars([rhs_e] + domain_exprs, explicit_params, named_funcs, eff_list_params) if v != arg_name
                ]
                if auto_vars and not auto_sliders_on:
                    return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None
                used_lists = _detect_used_lists([rhs_e] + domain_exprs, eff_list_params)
                if used_lists:
                    fam_expr = rhs_e if arg_name == "x" else rhs_e.subs(sp.Symbol(arg_name, real=True), X_SYM)
                    res = _eval_curve_family(fam_expr, used_lists, eff_list_params, lambda e: _finalize(e, auto_vars), vp, latex_str, num_registry, domain_chains)
                    res["auto_vars"] = auto_vars
                    return res, None, None
                ev_expr = _finalize(rhs_e, auto_vars)
                if arg_name != "x":
                    ev_expr = ev_expr.subs(sp.Symbol(arg_name, real=True), X_SYM)
                dom_fn, dom_bounds = _build_domain_mask_fn(domain_chains, lambda e: _finalize(e, auto_vars), num_registry)
                res, meta = _eval_explicit_curve(
                    ev_expr, vp, latex_str, num_registry,
                    domain_fn=dom_fn, domain_bounds=dom_bounds,
                    table_xs=table_xs, compute_kp=compute_kp,
                )
                res["auto_vars"] = auto_vars
                return res, meta, None

            if lhs_strip == "r":
                rhs_e = _parse_symbolic(rhs_s, named_funcs)
                rhs_exp = _expand_named_funcs(rhs_e, named_funcs, num_registry)
                latex_str = f"r = {sp.latex(rhs_e)}" + domain_tex
                auto_vars = _detect_auto_vars([rhs_exp] + domain_exprs, explicit_params, named_funcs, eff_list_params, bound_vars={"r", "theta"})
                if auto_vars and not auto_sliders_on:
                    return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None
                th_range = _extract_param_bounds(domain_chains, THETA_SYM, lambda e: _finalize(e, auto_vars), 0.0, 4.0 * np.pi)
                used_lists = _detect_used_lists([rhs_exp] + domain_exprs, eff_list_params)
                if used_lists:
                    n_c = min(len(eff_list_params[nm]) for nm in used_lists)
                    curves = []
                    for idx in range(min(n_c, SAMPLING_CONFIG.max_list_items)):
                        ss = {nm: eff_list_params[nm][idx] for nm in used_lists}
                        ev = _substitute_params(_finalize(rhs_exp, auto_vars), ss)
                        dom_fn = None
                        if domain_chains:
                            dom_fn, _ = _build_domain_mask_fn(domain_chains, lambda e, ss=ss: _substitute_params(_finalize(e, auto_vars), ss), num_registry)
                        curves.append(_eval_polar(ev, x_span, y_span, latex_str, num_registry, domain_fn=dom_fn, theta_range=th_range)["points"])
                    return {"kind": "curve_family", "curves": curves, "count": len(curves), "latex": latex_str, "auto_vars": auto_vars}, None, None
                dom_fn, _ = _build_domain_mask_fn(domain_chains, lambda e: _finalize(e, auto_vars), num_registry)
                res = _eval_polar(_finalize(rhs_exp, auto_vars), x_span, y_span, latex_str, num_registry, domain_fn=dom_fn, theta_range=th_range)
                res["auto_vars"] = auto_vars
                return res, None, None

            lhs_e = _parse_symbolic(lhs_s, named_funcs)
            rhs_e = _parse_symbolic(rhs_s, named_funcs)
            lhs_exp = _expand_named_funcs(lhs_e, named_funcs, num_registry)
            rhs_exp = _expand_named_funcs(rhs_e, named_funcs, num_registry)
            latex_str = f"{sp.latex(lhs_e)} = {sp.latex(rhs_e)}" + domain_tex
            auto_vars = _detect_auto_vars([lhs_exp, rhs_exp] + domain_exprs, explicit_params, named_funcs, eff_list_params)
            if auto_vars and not auto_sliders_on:
                return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None

            used_lists = _detect_used_lists([lhs_exp, rhs_exp] + domain_exprs, eff_list_params)
            if used_lists:
                if lhs_e == Y_SYM and Y_SYM not in rhs_e.free_symbols:
                    res = _eval_curve_family(rhs_e, used_lists, eff_list_params, lambda e: _finalize(e, auto_vars), vp, latex_str, num_registry, domain_chains)
                    res["auto_vars"] = auto_vars
                    return res, None, None
                if rhs_e == Y_SYM and Y_SYM not in lhs_e.free_symbols:
                    res = _eval_curve_family(lhs_e, used_lists, eff_list_params, lambda e: _finalize(e, auto_vars), vp, latex_str, num_registry, domain_chains)
                    res["auto_vars"] = auto_vars
                    return res, None, None
                res = _eval_implicit_family(
                    lhs_e - rhs_e, used_lists, eff_list_params,
                    lambda e: _finalize(e, auto_vars),
                    vp, latex_str, num_registry, domain_chains,
                )
                res["auto_vars"] = auto_vars
                return res, None, None

            dom_fn, dom_bounds = _build_domain_mask_fn(domain_chains, lambda e: _finalize(e, auto_vars), num_registry)

            if lhs_e == Y_SYM and Y_SYM not in rhs_e.free_symbols:
                res, meta = _eval_explicit_curve(
                    _finalize(rhs_e, auto_vars), vp, latex_str, num_registry,
                    domain_fn=dom_fn, domain_bounds=dom_bounds,
                    table_xs=table_xs, compute_kp=compute_kp,
                )
                res["auto_vars"] = auto_vars
                return res, meta, None
            if rhs_e == Y_SYM and Y_SYM not in lhs_e.free_symbols:
                res, meta = _eval_explicit_curve(
                    _finalize(lhs_e, auto_vars), vp, latex_str, num_registry,
                    domain_fn=dom_fn, domain_bounds=dom_bounds,
                    table_xs=table_xs, compute_kp=compute_kp,
                )
                res["auto_vars"] = auto_vars
                return res, meta, None

            if lhs_e == X_SYM and X_SYM not in rhs_e.free_symbols:
                res = _eval_explicit_x_of_y(
                    _finalize(rhs_e, auto_vars), vp, latex_str, num_registry, domain_fn=dom_fn
                )
                res["auto_vars"] = auto_vars
                return res, None, None
            if rhs_e == X_SYM and X_SYM not in lhs_e.free_symbols:
                res = _eval_explicit_x_of_y(
                    _finalize(lhs_e, auto_vars), vp, latex_str, num_registry, domain_fn=dom_fn
                )
                res["auto_vars"] = auto_vars
                return res, None, None

            diff_ev = _finalize(lhs_e - rhs_e, auto_vars)
            if Z_SYM in diff_ev.free_symbols:
                res = _eval_implicit_3d(diff_ev, vp, latex_str, num_registry)
                res["auto_vars"] = auto_vars
                return res, None, None

            res = _eval_implicit(
                diff_ev, vp, latex_str, num_registry, domain_fn=dom_fn
            )
            res["auto_vars"] = auto_vars
            return res, None, None

        pw = parse_piecewise_rhs(main_raw, named_funcs) if ":" in main_raw else None
        expr = pw if pw is not None else _parse_symbolic(cleaned, named_funcs)
        expr_exp = _expand_named_funcs(expr, named_funcs, num_registry)
        latex_str = sp.latex(expr) + domain_tex
        bvars_pure = {"x", "y", "z", "theta"} if (THETA_SYM in expr_exp.free_symbols and X_SYM not in expr_exp.free_symbols) else {"x", "y", "z"}
        auto_vars = _detect_auto_vars([expr_exp] + domain_exprs, explicit_params, named_funcs, eff_list_params, bound_vars=bvars_pure)
        if auto_vars and not auto_sliders_on:
            return {"kind": "needs_params", "missing": auto_vars, "latex": latex_str}, None, None

        if isinstance(expr, sp.Integral) and not domain_chains:
            ev_int = _finalize(expr, auto_vars)
            if isinstance(ev_int, sp.Integral):
                int_res = _eval_definite_integral_area(ev_int, vp, latex_str, num_registry)
                if int_res is not None:
                    int_res["auto_vars"] = auto_vars
                    return int_res, None, None

        used_lists = _detect_used_lists([expr_exp] + domain_exprs, eff_list_params)
        if used_lists and Y_SYM not in expr.free_symbols and THETA_SYM not in expr.free_symbols:
            res = _eval_curve_family(expr, used_lists, eff_list_params, lambda e: _finalize(e, auto_vars), vp, latex_str, num_registry, domain_chains)
            res["auto_vars"] = auto_vars
            return res, None, None

        ev_expr = _finalize(expr, auto_vars)
        dom_fn, dom_bounds = _build_domain_mask_fn(domain_chains, lambda e: _finalize(e, auto_vars), num_registry)

        if not ev_expr.free_symbols and not domain_chains:
            ev_done = _prepare_for_lambdify(ev_expr)
            fn = sp.lambdify((), ev_done, modules=[num_registry, "numpy"])
            val = float(_eval_numeric(fn, (1,))[0])
            if math.isfinite(val):
                return {"kind": "value", "value": val, "latex": latex_str, "auto_vars": auto_vars}, None, None

        if THETA_SYM in ev_expr.free_symbols and X_SYM not in ev_expr.free_symbols:
            res = _eval_polar(ev_expr, x_span, y_span, f"r = {latex_str}", num_registry)
            res["auto_vars"] = auto_vars
            return res, None, None

        if Z_SYM in ev_expr.free_symbols:
            res = _eval_implicit_3d(ev_expr, vp, f"{latex_str} = 0", num_registry)
            res["auto_vars"] = auto_vars
            return res, None, None

        if Y_SYM in ev_expr.free_symbols:
            res = _eval_implicit(ev_expr, vp, f"{latex_str} = 0", num_registry, domain_fn=dom_fn)
            res["auto_vars"] = auto_vars
            return res, None, None

        res, meta = _eval_explicit_curve(
            ev_expr, vp, latex_str, num_registry,
            domain_fn=dom_fn, domain_bounds=dom_bounds,
            table_xs=table_xs, compute_kp=compute_kp,
        )
        res["auto_vars"] = auto_vars
        return res, meta, None

    except Exception as exc:
        return {
            "kind": "error",
            "error": str(exc)[:140],
            "latex": raw_expr,
        }, None, None


def _pack_parametric_polyline(xs: np.ndarray, ys: np.ndarray, x_span: float, y_span: float) -> list:
    pts = []
    prev_x = None
    prev_y = None
    max_dx = x_span * 2.5
    max_dy = y_span * 2.5
    for x_val, y_val in zip(xs, ys):
        if not (math.isfinite(x_val) and math.isfinite(y_val)):
            if pts and pts[-1] is not None:
                pts.append(None)
            prev_x = prev_y = None
            continue
        if prev_y is not None:
            if abs(y_val - prev_y) > max_dy or abs(x_val - prev_x) > max_dx:
                if pts and pts[-1] is not None:
                    pts.append(None)
        pts.append([format_coord(x_val), format_coord(y_val)])
        prev_x, prev_y = x_val, y_val
    return pts


def _sample_adaptive_1d(fn, vmin: float, vmax: float, omin: float, omax: float, extra_pts: list[float] | None = None):
    v_span = max(vmax - vmin, 1e-300)
    o_span = max(omax - omin, 1e-300)
    o_mid = 0.5 * (omin + omax)

    pad_v = SAMPLING_CONFIG.overscan_ratio * v_span
    sv_min = max(vmin - pad_v, -1e295)
    sv_max = min(vmax + pad_v, 1e295)

    parts = [np.linspace(sv_min, sv_max, SAMPLING_CONFIG.base_samples_1d)]

    if extra_pts:
        eps = max(v_span * 1e-7, 1e-9)
        b_arr = []
        for bx in extra_pts:
            if sv_min <= bx <= sv_max:
                b_arr.extend([bx - eps, bx, bx + eps])
        if b_arr:
            parts.append(np.array(b_arr, dtype=float))

    if sv_min < 0.0 < sv_max:
        max_abs = max(abs(sv_min), abs(sv_max))
        hi_exp = min(math.log10(max_abs), 295.0)
        lo_exp = min(hi_exp - 12.0, -6.0)
        n_dec = max(24, int(min(520, (hi_exp - lo_exp) * 2.5)))
        mags = np.power(10.0, np.linspace(lo_exp, hi_exp, n_dec))
        pos_pts = mags[mags < sv_max]
        neg_pts = -mags[mags < abs(sv_min)]
        parts.extend([np.array([0.0]), pos_pts, neg_pts])

    vs = np.unique(np.concatenate(parts))
    os_arr = _eval_numeric(fn, vs.shape, vs)

    max_points = SAMPLING_CONFIG.max_adaptive_points
    for _round in range(14):
        if len(vs) >= max_points:
            break

        o0 = os_arr[:-1]
        o1 = os_arr[1:]
        v0 = vs[:-1]
        v1 = vs[1:]
        dv = v1 - v0
        fin0 = np.isfinite(o0)
        fin1 = np.isfinite(o1)
        both_fin = fin0 & fin1

        in0 = fin0 & (o0 >= omin - 0.25 * o_span) & (o0 <= omax + 0.25 * o_span)
        in1 = fin1 & (o1 >= omin - 0.25 * o_span) & (o1 <= omax + 0.25 * o_span)

        cross_vis = (in0 ^ in1) & (dv > np.maximum(np.abs(v0), np.abs(v1)) * 1e-7 + v_span * 1e-12)
        nan_edge = (fin0 ^ fin1) & (dv > np.maximum(np.abs(v0), np.abs(v1)) * 1e-7 + v_span * 1e-12)

        with np.errstate(all="ignore"):
            do = np.where(both_fin, np.abs(o1 - o0), 0.0)
        straddle = both_fin & (((o0 < omin) & (o1 > omax)) | ((o0 > omax) & (o1 < omin))) & (dv > v_span * 1e-10)
        steep = both_fin & (in0 | in1) & (do > 0.22 * o_span) & (dv > v_span * 1e-7)

        dist = np.where(np.isfinite(os_arr), np.abs(os_arr - o_mid), np.inf)
        near_min = np.zeros(len(vs) - 1, dtype=bool)
        if len(vs) >= 3:
            is_loc_min = (dist[1:-1] <= dist[:-2]) & (dist[1:-1] <= dist[2:]) & np.isfinite(dist[1:-1])
            out_of_view_min = is_loc_min & (dist[1:-1] > 0.45 * o_span)
            min_indices = np.nonzero(out_of_view_min)[0] + 1
            for mi in min_indices[:8]:
                if dv[mi - 1] > v_span * 1e-12:
                    near_min[mi - 1] = True
                if mi < len(dv) and dv[mi] > v_span * 1e-12:
                    near_min[mi] = True

        need = cross_vis | nan_edge | straddle | steep | near_min
        idxs = np.nonzero(need)[0]
        if len(idxs) == 0:
            break

        if len(idxs) > 220:
            prio = np.nonzero(near_min | straddle | cross_vis | nan_edge)[0]
            if len(prio) >= 220:
                idxs = prio[:220]
            else:
                rest = np.nonzero(steep & ~(near_min | straddle | cross_vis | nan_edge))[0]
                step_pick = max(1, len(rest) // max(1, 220 - len(prio)))
                idxs = np.unique(np.concatenate([prio, rest[::step_pick][: 220 - len(prio)]]))

        a = vs[idxs]
        b = vs[idxs + 1]
        same_sign = (a * b) > 0.0
        with np.errstate(all="ignore"):
            ratio = np.where(same_sign, np.maximum(np.abs(a), np.abs(b)) / np.maximum(np.minimum(np.abs(a), np.abs(b)), 1e-300), 1.0)
            geom = np.sign(a) * np.sqrt(np.abs(a) * np.abs(b))
        mids = np.where(same_sign & (ratio > 10.0) & np.isfinite(geom), geom, 0.5 * (a + b))
        mids = mids[(mids > a) & (mids < b)]
        if len(mids) == 0:
            break

        mid_os = _eval_numeric(fn, mids.shape, mids)
        vs = np.concatenate([vs, mids])
        os_arr = np.concatenate([os_arr, mid_os])
        order = np.argsort(vs)
        vs = vs[order]
        os_arr = os_arr[order]

    return vs, os_arr


def _pack_adaptive_polyline(
    vs: np.ndarray,
    os_arr: np.ndarray,
    vmin: float,
    vmax: float,
    omin: float,
    omax: float,
    swap_xy: bool = False,
    has_steps: bool = False,
    keep_all_finite: bool = False,
) -> list:
    v_span = max(vmax - vmin, 1e-300)
    o_span = max(omax - omin, 1e-300)
    o_lo = omin - 0.6 * o_span
    o_hi = omax + 0.6 * o_span
    n = len(vs)

    pts = []
    in_seg = False

    def _emit_point(v_val, o_val):
        if swap_xy:
            pts.append([format_coord(o_val), format_coord(v_val)])
        else:
            pts.append([format_coord(v_val), format_coord(o_val)])

    def _break_seg():
        nonlocal in_seg
        if in_seg and pts and pts[-1] is not None:
            pts.append(None)
        in_seg = False

    for i in range(n - 1):
        v0, v1 = float(vs[i]), float(vs[i + 1])
        o0, o1 = float(os_arr[i]), float(os_arr[i + 1])

        if not (math.isfinite(o0) and math.isfinite(o1)):
            _break_seg()
            continue

        if not keep_all_finite and ((o0 > o_hi and o1 > o_hi) or (o0 < o_lo and o1 < o_lo)):
            _break_seg()
            continue

        d_jump = o1 - o0
        abs_jump = abs(d_jump)
        is_discontinuity = False

        if abs_jump > 0.75 * o_span:
            d_left = (o0 - float(os_arr[i - 1])) if (i > 0 and math.isfinite(os_arr[i - 1])) else 0.0
            d_right = (float(os_arr[i + 2]) - o1) if (i + 2 < n and math.isfinite(os_arr[i + 2])) else 0.0

            if (d_left * d_jump < 0.0) and (d_right * d_jump < 0.0):
                is_discontinuity = True
            elif (o0 * o1 < 0.0) and (
                abs(o0) > 1e7 * max(o_span, 1.0) or abs(o1) > 1e7 * max(o_span, 1.0)
            ):
                is_discontinuity = True

        if not is_discontinuity and has_steps and abs_jump >= 0.4 and (v1 - v0) < v_span * 5e-3:
            d_left = abs(o0 - float(os_arr[i - 1])) if (i > 0 and math.isfinite(os_arr[i - 1])) else 0.0
            d_right = abs(float(os_arr[i + 2]) - o1) if (i + 2 < n and math.isfinite(os_arr[i + 2])) else 0.0
            if d_left < 0.05 * abs_jump and d_right < 0.05 * abs_jump:
                is_discontinuity = True

        if is_discontinuity:
            _break_seg()
            continue

        if not in_seg:
            _emit_point(v0, o0)
            in_seg = True
        _emit_point(v1, o1)

    return pts


def _eval_explicit_curve(
    expr,
    vp: ViewportBounds,
    latex_str: str,
    num_registry: dict,
    ineq: str | None = None,
    strict: bool = False,
    domain_fn=None,
    domain_bounds: list[float] | None = None,
    table_xs: list | None = None,
    compute_kp: bool = True,
) -> tuple[dict, dict | None]:
    ev = _prepare_for_lambdify(expr)
    has_steps = ev.has(sp.floor, sp.ceiling, sp.sign, sp.Piecewise)
    fn = sp.lambdify(X_SYM, ev, modules=[num_registry, "numpy"])
    xs, ys = _sample_adaptive_1d(fn, vp.xmin, vp.xmax, vp.ymin, vp.ymax, extra_pts=domain_bounds)

    if domain_fn is not None:
        mask = domain_fn(xs, ys)
        ys[~mask] = np.nan

    pts = _pack_adaptive_polyline(
        xs, ys, vp.xmin, vp.xmax, vp.ymin, vp.ymax,
        swap_xy=False,
        has_steps=has_steps,
        keep_all_finite=bool(ineq),
    )

    res: dict = {
        "kind": "curve",
        "points": pts,
        "latex": latex_str,
        "supports_table": ineq is None,
    }
    if ineq:
        res["inequality"] = ineq
        res["strict"] = strict

    if table_xs is not None and ineq is None:
        t_rows = []
        for raw_x in table_xs:
            try:
                xv = float(raw_x)
                yv = _eval_scalar_masked(fn, domain_fn, xv)
                t_rows.append([format_coord(xv), format_coord(yv) if math.isfinite(yv) else None])
            except Exception:
                t_rows.append([raw_x, None])
        res["table"] = t_rows

    meta = None
    if ineq is None:
        if compute_kp:
            res["key_points"] = _compute_curve_keypoints(fn, domain_fn, vp)
        meta = {"fn": fn, "domain_fn": domain_fn}

    return res, meta


def _eval_explicit_x_of_y(expr, vp: ViewportBounds, latex_str: str, num_registry: dict, domain_fn=None):
    ev = _prepare_for_lambdify(expr)
    has_steps = ev.has(sp.floor, sp.ceiling, sp.sign, sp.Piecewise)
    fn = sp.lambdify(Y_SYM, ev, modules=[num_registry, "numpy"])
    ys, xs = _sample_adaptive_1d(fn, vp.ymin, vp.ymax, vp.xmin, vp.xmax)
    if domain_fn is not None:
        xs[~domain_fn(xs, ys)] = np.nan
    pts = _pack_adaptive_polyline(
        ys, xs, vp.ymin, vp.ymax, vp.xmin, vp.xmax,
        swap_xy=True,
        has_steps=has_steps,
    )
    return {"kind": "curve", "points": pts, "latex": latex_str}


def _eval_polar(
    expr,
    x_span: float,
    y_span: float,
    latex_str: str,
    num_registry: dict,
    domain_fn=None,
    theta_range: tuple[float, float] = (0.0, 4.0 * np.pi),
):
    ev = _prepare_for_lambdify(expr)
    fn = sp.lambdify(THETA_SYM, ev, modules=[num_registry, "numpy"])
    thetas = np.linspace(theta_range[0], theta_range[1], SAMPLING_CONFIG.polar_samples)
    rs = _eval_numeric(fn, thetas.shape, thetas)
    xs = rs * np.cos(thetas)
    ys = rs * np.sin(thetas)
    if domain_fn is not None:
        mask = domain_fn(xs, ys, theta_arr=thetas)
        xs[~mask] = np.nan
        ys[~mask] = np.nan
    pts = _pack_parametric_polyline(xs, ys, x_span, y_span)
    return {"kind": "curve", "points": pts, "latex": latex_str}


def _probe_implicit_origin(fn, max_r: float) -> list:
    hi_exp = min(math.log10(max(max_r, 1e-6)), 145.0)
    radii = np.concatenate([[0.0], np.power(10.0, np.linspace(-4.0, hi_exp, 120))])
    angles = np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False)
    R, A = np.meshgrid(radii, angles)
    PX = R * np.cos(A)
    PY = R * np.sin(A)
    PZ = _eval_numeric(fn, PX.shape, PX, PY)

    found_r = None
    for ri in range(len(radii) - 1):
        col0 = PZ[:, ri]
        col1 = PZ[:, ri + 1]
        fin = np.isfinite(col0) & np.isfinite(col1)
        if np.any(fin & ((col0 > 0) != (col1 > 0))):
            found_r = float(radii[ri + 1])
            break
        fin1 = np.isfinite(col1)
        if np.any(fin1) and np.any(col1[fin1] > 0) and np.any(col1[fin1] < 0):
            found_r = float(radii[ri + 1])
            break

    if found_r is not None and found_r > 0.0:
        box = found_r * 2.5
        gx = np.linspace(-box, box, 45)
        gy = np.linspace(-box, box, 45)
        X, Y = np.meshgrid(gx, gy)
        Z = _eval_numeric(fn, X.shape, X, Y)
        segs = marching_squares(X, Y, Z)
        if segs:
            return segs
    return []


def _refine_implicit_cell(fn, xa: float, xb: float, ya: float, yb: float, max_depth: int = 45) -> list:
    cx0, cx1, cy0, cy1 = xa, xb, ya, yb
    for _ in range(max_depth):
        dx = cx1 - cx0
        dy = cy1 - cy0
        if dx <= 0.0 or dy <= 0.0:
            break
        sgx = np.linspace(cx0, cx1, 13)
        sgy = np.linspace(cy0, cy1, 13)
        SX, SY = np.meshgrid(sgx, sgy)
        SZ = _eval_numeric(fn, SX.shape, SX, SY)
        sub_segs = marching_squares(SX, SY, SZ)
        if sub_segs:
            return sub_segs

        abs_z = np.where(np.isfinite(SZ), np.abs(SZ), np.inf)
        flat_idx = int(np.argmin(abs_z))
        if not math.isfinite(float(abs_z.ravel()[flat_idx])):
            break
        r, c = divmod(flat_idx, 13)
        c0 = max(0, c - 1)
        c1 = min(12, c + 1)
        r0 = max(0, r - 1)
        r1 = min(12, r + 1)
        nx0, nx1 = float(sgx[c0]), float(sgx[c1])
        ny0, ny1 = float(sgy[r0]), float(sgy[r1])
        if (nx1 - nx0) >= dx * 0.99 or (ny1 - ny0) >= dy * 0.99:
            break
        cx0, cx1, cy0, cy1 = nx0, nx1, ny0, ny1
    return []


def _eval_implicit(
    diff_expr,
    vp: ViewportBounds,
    latex_str: str,
    num_registry: dict,
    ineq_op: str | None = None,
    strict: bool = False,
    domain_fn=None,
):
    xmin, xmax, ymin, ymax = vp.xmin, vp.xmax, vp.ymin, vp.ymax
    ev = _prepare_for_lambdify(diff_expr)
    fn = sp.lambdify((X_SYM, Y_SYM), ev, modules=[num_registry, "numpy"])
    nx, ny = SAMPLING_CONFIG.implicit_nx, SAMPLING_CONFIG.implicit_ny
    gx = np.linspace(xmin, xmax, nx)
    gy = np.linspace(ymin, ymax, ny)
    X, Y = np.meshgrid(gx, gy)
    Z = _eval_numeric(fn, X.shape, X, Y)
    if domain_fn is not None:
        Z[~domain_fn(X, Y)] = np.nan
    segs = marching_squares(X, Y, Z)

    if len(segs) < 12 and domain_fn is None:
        if vp.contains_origin():
            max_r = min(max(abs(xmin), abs(xmax)), max(abs(ymin), abs(ymax)))
            origin_segs = _probe_implicit_origin(fn, max_r)
            if origin_segs:
                segs.extend(origin_segs)

        if len(segs) < 12:
            candidates = []
            abs_z = np.where(np.isfinite(Z), np.abs(Z), np.inf)
            min_flat = int(np.argmin(abs_z))
            if math.isfinite(float(abs_z.ravel()[min_flat])):
                mr, mc = divmod(min_flat, nx)
                candidates.append((mr, mc))

            if ny >= 3 and nx >= 3:
                center = abs_z[1:-1, 1:-1]
                loc = (
                    np.isfinite(center)
                    & (center <= abs_z[:-2, 1:-1])
                    & (center <= abs_z[2:, 1:-1])
                    & (center <= abs_z[1:-1, :-2])
                    & (center <= abs_z[1:-1, 2:])
                )
                lr, lc = np.nonzero(loc)
                if len(lr) > 0:
                    order = np.argsort(center[lr, lc])[:4]
                    for oi in order:
                        rc = (int(lr[oi]) + 1, int(lc[oi]) + 1)
                        if rc not in candidates:
                            candidates.append(rc)

            for r, c in candidates[:4]:
                c0 = max(0, c - 1)
                c1 = min(nx - 1, c + 1)
                r0 = max(0, r - 1)
                r1 = min(ny - 1, r + 1)
                sub_segs = _refine_implicit_cell(fn, float(gx[c0]), float(gx[c1]), float(gy[r0]), float(gy[r1]))
                if sub_segs:
                    segs.extend(sub_segs)

    res: dict = {
        "kind": "implicit",
        "segments": segs,
        "latex": latex_str,
        "strict": strict,
    }
    if ineq_op is not None:
        mx, my = SAMPLING_CONFIG.shade_mx, SAMPLING_CONFIG.shade_my
        sx = np.linspace(xmin, xmax, mx)
        sy = np.linspace(ymin, ymax, my)
        SX, SY = np.meshgrid(sx, sy)
        SZ = _eval_numeric(fn, SX.shape, SX, SY)
        if ineq_op == "<":
            mask = SZ < 0
        elif ineq_op == "<=":
            mask = SZ <= 0
        elif ineq_op == ">":
            mask = SZ > 0
        else:
            mask = SZ >= 0
        if domain_fn is not None:
            mask &= domain_fn(SX, SY)
        mask = np.flipud(mask)
        res["shade"] = {
            "w": mx,
            "h": my,
            "bounds": [format_coord(xmin), format_coord(xmax), format_coord(ymin), format_coord(ymax)],
            "bits": "".join("1" if b else "0" for b in mask.ravel()),
        }
    return res

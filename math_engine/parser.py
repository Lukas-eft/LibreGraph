from __future__ import annotations

import re

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


X_SYM, Y_SYM, Z_SYM, T_SYM, THETA_SYM, R_SYM, U_SYM, V_SYM = sp.symbols("x y z t theta r u v", real=True)
RESERVED_SYMS = {"x", "y", "z", "t", "theta", "r", "e", "pi", "i", "oo"}
BUILTIN_FUNC_NAMES = {
    "sin", "cos", "tan", "asin", "acos", "atan", "arcsin", "arccos", "arctan",
    "sinh", "cosh", "tanh", "sec", "csc", "cot", "exp", "ln", "log",
    "sqrt", "nthroot", "factorial", "gamma", "abs", "Abs",
    "floor", "ceil", "ceiling", "sign", "ddx", "diff",
    "Sum", "Product", "Integral",
}

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


class nthroot(sp.Function):

    @classmethod
    def eval(cls, x, n):
        return None

    def _latex(self, printer):
        return rf"\sqrt[{printer._print(self.args[1])}]{{{printer._print(self.args[0])}}}"


_LANCZOS_P = (
    0.99999999999980993,
    676.5203681218851,
    -1259.1392167224028,
    771.32342877765313,
    -176.61502916214059,
    12.507343278686905,
    -0.13857109526572012,
    9.9843695780195716e-6,
    1.5056327351493116e-7,
)


def _np_gamma_pos(z: np.ndarray) -> np.ndarray:
    z1 = z - 1.0
    acc = np.full_like(z1, _LANCZOS_P[0], dtype=float)
    for idx in range(1, len(_LANCZOS_P)):
        acc = acc + _LANCZOS_P[idx] / (z1 + idx)
    t = z1 + 7.5
    return np.sqrt(2.0 * np.pi) * np.power(t, z1 + 0.5) * np.exp(-t) * acc


def _np_gamma(z):
    arr = np.asarray(z, dtype=float)
    scalar = arr.ndim == 0
    arr = np.atleast_1d(arr)
    out = np.full_like(arr, np.nan, dtype=float)
    with np.errstate(all="ignore"):
        poles = (arr <= 0.0) & (np.abs(arr - np.round(arr)) < 1e-7)
        valid = np.isfinite(arr) & (~poles) & (arr < 171.5)
        pos = valid & (arr >= 0.5)
        neg = valid & (arr < 0.5)
        if np.any(pos):
            out[pos] = _np_gamma_pos(arr[pos])
        if np.any(neg):
            zn = arr[neg]
            out[neg] = np.pi / (np.sin(np.pi * zn) * _np_gamma_pos(1.0 - zn))
    return float(out[0]) if scalar else out


def _np_factorial(x):
    return _np_gamma(np.asarray(x, dtype=float) + 1.0)


def _np_nthroot(val, n):
    v = np.asarray(val, dtype=float)
    nv = np.asarray(n, dtype=float)
    with np.errstate(all="ignore"):
        rounded = np.round(nv)
        is_odd = np.isfinite(nv) & (np.abs(nv - rounded) < 1e-9) & (np.mod(rounded, 2) != 0)
        return np.where(is_odd & (v < 0), -np.power(np.abs(v), 1.0 / nv), np.power(v, 1.0 / nv))


BASE_NUMPY_MAP = {
    "nthroot": _np_nthroot,
    "factorial": _np_factorial,
    "gamma": _np_gamma,
}


def _read_balanced(text: str, pos: int, open_ch: str, close_ch: str):
    if pos >= len(text) or text[pos] != open_ch:
        return None
    depth = 0
    start = pos + 1
    i = pos
    while i < len(text):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    return None


def _read_script_arg(text: str, pos: int, read_number: bool = False):
    while pos < len(text) and text[pos] == " ":
        pos += 1
    if pos >= len(text):
        return None
    if text[pos] == "{":
        return _read_balanced(text, pos, "{", "}")
    if text[pos] == "\\":
        m = re.match(r"\\[a-zA-Z]+", text[pos:])
        if m:
            return m.group(0), pos + m.end()
    if read_number:
        m = re.match(r"-?\d+(?:\.\d+)?", text[pos:])
        if m:
            return m.group(0), pos + m.end()
    return text[pos], pos + 1


def _read_operator_body(text: str, pos: int):
    while pos < len(text) and text[pos] == " ":
        pos += 1
    if pos >= len(text):
        return "", pos
    depth_p = 0
    depth_b = 0
    i = pos
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth_p += 1
        elif ch == ")":
            if depth_p == 0:
                break
            depth_p -= 1
        elif ch == "{":
            depth_b += 1
        elif ch == "}":
            if depth_b == 0:
                break
            depth_b -= 1
        elif depth_p == 0 and depth_b == 0 and ch in ("=", "<", ">", ","):
            break
        i += 1
    return text[pos:i].strip(), i


def _replace_latex_command(text: str, cmd: str, num_args: int, formatter) -> str:
    token = "\\" + cmd
    while True:
        idx = text.find(token)
        if idx == -1:
            break
        pos = idx + len(token)
        args = []
        ok = True
        for _ in range(num_args):
            res = _read_script_arg(text, pos)
            if res is None:
                ok = False
                break
            arg, pos = res
            args.append(arg)
        if not ok:
            break
        replacement = formatter(*args)
        text = text[:idx] + replacement + text[pos:]
    return text


def _replace_nth_roots(text: str) -> str:
    while True:
        idx = text.find("\\sqrt[")
        if idx == -1:
            break
        res_n = _read_balanced(text, idx + 5, "[", "]")
        if res_n is None:
            break
        n_str, pos = res_n
        res_x = _read_script_arg(text, pos)
        if res_x is None:
            break
        x_str, end_pos = res_x
        if not n_str.strip() or not x_str.strip():
            return "__INCOMPLETE__"
        n_clean = preprocess_latex(n_str)
        x_clean = preprocess_latex(x_str)
        if n_clean == "__INCOMPLETE__" or x_clean == "__INCOMPLETE__":
            return "__INCOMPLETE__"
        text = text[:idx] + f"nthroot(({x_clean}), ({n_clean}))" + text[end_pos:]
    return text


def _replace_log_base(text: str) -> str:
    while True:
        idx = text.find("\\log_")
        if idx == -1:
            break
        res_b = _read_script_arg(text, idx + 5)
        if res_b is None:
            break
        base_str, pos = res_b
        while pos < len(text) and text[pos] == " ":
            pos += 1
        res_x = _read_balanced(text, pos, "(", ")")
        if res_x is None:
            res_x = _read_script_arg(text, pos, read_number=True)
        if res_x is None:
            break
        arg_str, end_pos = res_x
        if not base_str.strip() or not arg_str.strip():
            return "__INCOMPLETE__"
        b_clean = preprocess_latex(base_str)
        x_clean = preprocess_latex(arg_str)
        if b_clean == "__INCOMPLETE__" or x_clean == "__INCOMPLETE__":
            return "__INCOMPLETE__"
        text = text[:idx] + f"log(({x_clean}), ({b_clean}))" + text[end_pos:]
    return text


def _replace_sum_prod(text: str, cmd: str, sympy_cls: str) -> str:
    token = "\\" + cmd
    while True:
        idx = text.find(token)
        if idx == -1:
            break
        pos = idx + len(token)
        sub_str = None
        sup_str = None

        for _ in range(2):
            while pos < len(text) and text[pos] == " ":
                pos += 1
            if pos < len(text) and text[pos] == "_" and sub_str is None:
                res = _read_script_arg(text, pos + 1)
                if res is None:
                    break
                sub_str, pos = res
            elif pos < len(text) and text[pos] == "^" and sup_str is None:
                res = _read_script_arg(text, pos + 1)
                if res is None:
                    break
                sup_str, pos = res
            else:
                break

        body_raw, end_pos = _read_operator_body(text, pos)

        if (sup_str is not None and not sup_str.strip()) or not body_raw.strip():
            return "__INCOMPLETE__"

        var_name = "n"
        low_raw = "1"
        if sub_str is not None:
            if not sub_str.strip():
                return "__INCOMPLETE__"
            if "=" in sub_str:
                v_part, l_part = sub_str.split("=", 1)
                var_name = v_part.strip() or "n"
                low_raw = l_part.strip()
                if not low_raw:
                    return "__INCOMPLETE__"
            else:
                low_raw = sub_str.strip()

        high_raw = sup_str.strip() if sup_str is not None else "5"

        body_clean = preprocess_latex(body_raw)
        low_clean = preprocess_latex(low_raw)
        high_clean = preprocess_latex(high_raw)
        if "__INCOMPLETE__" in (body_clean, low_clean, high_clean):
            return "__INCOMPLETE__"

        replacement = f"{sympy_cls}(({body_clean}), ({var_name}, {low_clean}, {high_clean}))"
        text = text[:idx] + replacement + text[end_pos:]
    return text


def _replace_integrals(text: str) -> str:
    token = "\\int"
    while True:
        idx = text.find(token)
        if idx == -1:
            break
        pos = idx + len(token)
        sub_str = None
        sup_str = None

        for _ in range(2):
            while pos < len(text) and text[pos] == " ":
                pos += 1
            if pos < len(text) and text[pos] == "_" and sub_str is None:
                res = _read_script_arg(text, pos + 1)
                if res is None:
                    break
                sub_str, pos = res
            elif pos < len(text) and text[pos] == "^" and sup_str is None:
                res = _read_script_arg(text, pos + 1)
                if res is None:
                    break
                sup_str, pos = res
            else:
                break

        while pos < len(text) and text[pos] == " ":
            pos += 1
        depth_p = 0
        depth_b = 0
        i = pos
        found_diff = None
        while i < len(text):
            ch = text[i]
            if ch == "(":
                depth_p += 1
            elif ch == ")":
                if depth_p == 0:
                    break
                depth_p -= 1
            elif ch == "{":
                depth_b += 1
            elif ch == "}":
                if depth_b == 0:
                    break
                depth_b -= 1
            elif depth_p == 0 and depth_b == 0:
                if ch in ("=", "<", ">", ","):
                    break
                if ch == "d":
                    prev_ch = text[i - 1] if i > pos else ""
                    is_cmd = False
                    if prev_ch == "\\":
                        is_cmd = True
                    elif prev_ch.isalpha():
                        k = i - 1
                        while k >= pos and text[k].isalpha():
                            k -= 1
                        if k >= pos and text[k] == "\\":
                            is_cmd = True
                        elif (i - 1 - k) >= 2:
                            is_cmd = True
                    if not is_cmd:
                        m_d = re.match(r"d\s*([a-zA-Z])(?![a-zA-Z])", text[i:])
                        if m_d and i > pos:
                            found_diff = (i, i + m_d.end(), m_d.group(1))
                            break
            i += 1

        if found_diff is not None:
            d_start, end_pos, var_name = found_diff
            body_raw = text[pos:d_start].strip()
        else:
            body_raw = text[pos:i].strip()
            end_pos = i
            var_name = "x"

        if not body_raw.strip():
            return "__INCOMPLETE__"
        if (sub_str is not None and not sub_str.strip()) or (sup_str is not None and not sup_str.strip()):
            return "__INCOMPLETE__"

        body_clean = preprocess_latex(body_raw)
        if body_clean == "__INCOMPLETE__":
            return "__INCOMPLETE__"

        if sub_str is not None and sup_str is not None:
            low_clean = preprocess_latex(sub_str)
            high_clean = preprocess_latex(sup_str)
            if "__INCOMPLETE__" in (low_clean, high_clean):
                return "__INCOMPLETE__"
            replacement = f"Integral(({body_clean}), ({var_name}, {low_clean}, {high_clean}))"
        else:
            replacement = f"Integral(({body_clean}), {var_name})"
        text = text[:idx] + replacement + text[end_pos:]
    return text


def _replace_factorials(text: str) -> str:
    i = 0
    while i < len(text):
        if text[i] == "!" and (i + 1 >= len(text) or text[i + 1] != "="):
            j = i - 1
            while j >= 0 and text[j] == " ":
                j -= 1
            if j < 0:
                i += 1
                continue
            if text[j] == ")":
                depth = 0
                k = j
                while k >= 0:
                    if text[k] == ")":
                        depth += 1
                    elif text[k] == "(":
                        depth -= 1
                        if depth == 0:
                            break
                    k -= 1
                if k >= 0:
                    inner = text[k + 1 : j]
                    rep = f"factorial({inner})"
                    text = text[:k] + rep + text[i + 1 :]
                    i = k + len(rep)
                    continue
            else:
                k = j
                while k >= 0 and (text[k].isalnum() or text[k] in ("_", ".")):
                    k -= 1
                start = k + 1
                if start <= j:
                    atom = text[start : j + 1]
                    rep = f"factorial({atom})"
                    text = text[:start] + rep + text[i + 1 :]
                    i = start + len(rep)
                    continue
        i += 1
    return text


_POWER_FUNCS_RE = re.compile(
    r"\b(sinh|cosh|tanh|sin|cos|tan|sec|csc|cot|ln|log)\s*(\*\*|\^)"
)


def _replace_func_powers(text: str) -> str:
    inv_map = {"sin": "asin", "cos": "acos", "tan": "atan"}
    pos = 0
    while True:
        m = _POWER_FUNCS_RE.search(text, pos)
        if not m:
            break
        fn_name = m.group(1)
        idx = m.start()
        p = m.end()
        while p < len(text) and text[p] == " ":
            p += 1
        if p >= len(text):
            break

        if text[p] == "(":
            res_exp = _read_balanced(text, p, "(", ")")
            if res_exp is None:
                pos = m.end()
                continue
            exp_str, p = res_exp
        else:
            exp_start = p
            if text[p] == "-":
                p += 1
            while p < len(text) and (text[p].isalnum() or text[p] == "."):
                p += 1
            exp_str = text[exp_start:p]
            if not exp_str:
                pos = m.end()
                continue

        while p < len(text) and text[p] == " ":
            p += 1
        if p >= len(text):
            pos = m.end()
            continue

        if text[p] == "(":
            res_arg = _read_balanced(text, p, "(", ")")
            if res_arg is None:
                pos = m.end()
                continue
            arg_str, end_pos = res_arg
        else:
            arg_start = p
            while p < len(text) and (text[p].isalnum() or text[p] in ("_", ".")):
                p += 1
            arg_str = text[arg_start:p]
            end_pos = p
            if not arg_str:
                pos = m.end()
                continue

        exp_clean = exp_str.strip()
        if fn_name in inv_map and exp_clean in ("-1", "(-1)"):
            rep = f"{inv_map[fn_name]}({arg_str})"
        else:
            rep = f"({fn_name}({arg_str}))**({exp_clean})"

        text = text[:idx] + rep + text[end_pos:]
        pos = idx + len(rep)

    return text


def _replace_subscripts(text: str) -> str:
    while True:
        m = re.search(r"([a-zA-Z][a-zA-Z0-9_]*)_\s*\{([a-zA-Z0-9_]+)\}", text)
        if not m:
            break
        text = text[: m.start()] + f"{m.group(1)}_{m.group(2)}" + text[m.end() :]
    return text


def _replace_abs_bars(text: str) -> str:
    if "|" not in text:
        return text
    out = []
    open_abs = 0
    prev_non_space = ""
    for ch in text:
        if ch == "|":
            if open_abs == 0 or prev_non_space in ("", "(", "[", "{", "+", "-", "*", "/", "^", ",", "=", "<", ">", "|"):
                out.append("Abs(")
                open_abs += 1
                prev_non_space = "("
            else:
                out.append(")")
                open_abs -= 1
                prev_non_space = ")"
        else:
            out.append(ch)
            if not ch.isspace():
                prev_non_space = ch
    return "".join(out)


def preprocess_latex(raw: str) -> str:
    s = raw.strip()
    if not s:
        return ""
    if "\\placeholder" in s:
        return "__INCOMPLETE__"

    s = (
        s.replace("\\limits", "")
        .replace("\\nolimits", "")
        .replace("\\displaystyle", "")
        .replace("\\textstyle", "")
        .replace("\\left|", "|")
        .replace("\\right|", "|")
        .replace("\\left", "")
        .replace("\\right", "")
        .replace("\\mathrm{d}", " d")
        .replace("\\differentialD", " d")
        .replace("\\exponentialE", " e ")
        .replace("\\,", " ")
        .replace("\\;", " ")
        .replace("\\:", " ")
        .replace("\\!", " ")
        .replace("\\ ", " ")
    )
    s = re.sub(r"\\operatorname\s*\{([a-zA-Z]+)\}", r" \1 ", s)

    s = (
        s.replace("′", "'")
        .replace("’", "'")
        .replace("^{\\prime\\prime\\prime}", "'" * 3)
        .replace("^{\\prime\\prime}", "'" * 2)
        .replace("^{\\prime}", "'")
        .replace("\\prime", "'")
    )
    s = re.sub(
        r"(?<![a-zA-Z_])([a-zA-Z][a-zA-Z0-9_]*)('{1,3})(?=\s*\()",
        lambda m: f" __deriv{len(m.group(2))}_{m.group(1)}",
        s,
    )

    s = _replace_sum_prod(s, "sum", "Sum")
    if s == "__INCOMPLETE__":
        return s
    s = _replace_sum_prod(s, "prod", "Product")
    if s == "__INCOMPLETE__":
        return s
    s = _replace_integrals(s)
    if s == "__INCOMPLETE__":
        return s
    s = _replace_nth_roots(s)
    if s == "__INCOMPLETE__":
        return s
    s = _replace_log_base(s)
    if s == "__INCOMPLETE__":
        return s

    replacements = [
        ("\\cdot", "*"),
        ("\\times", "*"),
        ("\\div", "/"),
        ("·", "*"),
        ("×", "*"),
        ("÷", "/"),
        ("−", "-"),
        ("–", "-"),
        ("\\pi", " pi "),
        ("π", " pi "),
        ("\\theta", " theta "),
        ("θ", " theta "),
        ("\\sigma", " sigma "),
        ("σ", " sigma "),
        ("\\mu", " mu "),
        ("μ", " mu "),
        ("\\alpha", " alpha "),
        ("α", " alpha "),
        ("\\beta", " beta "),
        ("β", " beta "),
        ("\\phi", " phi "),
        ("φ", " phi "),
        ("\\omega", " omega "),
        ("ω", " omega "),
        ("\\Delta", " Delta "),
        ("Δ", " Delta "),
        ("\\leq", "<="),
        ("\\le", "<="),
        ("≤", "<="),
        ("\\geq", ">="),
        ("\\ge", ">="),
        ("≥", ">="),
        ("\\infty", " oo "),
        ("∞", " oo "),
        ("\\lfloor", "floor("),
        ("\\rfloor", ")"),
        ("\\lceil", "ceiling("),
        ("\\rceil", ")"),
    ]
    for old, new in replacements:
        s = s.replace(old, new)

    s = re.sub(r"\\frac\s*\{\s*d\s*\}\s*\{\s*d\s*x\s*\}", "ddx", s)
    s = re.sub(r"\bd\s*/\s*d\s*x\b", "ddx", s)

    s = _replace_latex_command(s, "frac", 2, lambda a, b: f"(({a})/({b}))")
    s = _replace_latex_command(s, "sqrt", 1, lambda a: f"sqrt({a})")

    funcs = [
        "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh",
        "sin", "cos", "tan", "sec", "csc", "cot",
        "asin", "acos", "atan", "exp", "ln", "log",
        "abs", "floor", "ceil", "sign",
    ]
    for fn in funcs:
        s = re.sub(rf"\\{fn}(?=[a-zA-Z0-9\\])", f" {fn} ", s)
        s = s.replace("\\" + fn, f" {fn}")

    while "^{" in s:
        idx = s.find("^{")
        res = _read_balanced(s, idx + 1, "{", "}")
        if res is None:
            break
        inner, end_pos = res
        if not inner.strip():
            return "__INCOMPLETE__"
        s = s[:idx] + f"**({inner})" + s[end_pos:]

    s = _replace_subscripts(s)
    s = s.replace("{", "(").replace("}", ")")
    s = _replace_func_powers(s)
    s = _replace_abs_bars(s)

    s = _replace_factorials(s)

    s = re.sub(r"\barcsin\b", "asin", s)
    s = re.sub(r"\barccos\b", "acos", s)
    s = re.sub(r"\barctan\b", "atan", s)
    s = re.sub(r"\bceil\b", "ceiling", s)

    return s.strip()


def _make_placeholder_func(display_name: str, prime_count: int = 0):
    primes = "'" * prime_count
    cls_name = f"__UserFn_{display_name}_{prime_count}"

    class _UserFn(sp.Function):
        _user_fname = display_name
        _user_order = prime_count

        @classmethod
        def eval(cls, *args):
            return None

        def _latex(self, printer):
            args_tex = ", ".join(printer._print(a) for a in self.args)
            return rf"{display_name}{primes}\left({args_tex}\right)"

    _UserFn.__name__ = cls_name
    return _UserFn


def _real_symbol(name: str):
    return sp.Symbol(name, real=True)


SAFE_SYMPY_GLOBALS = {
    "Symbol": _real_symbol,
    "Function": sp.Function,
    "Integer": sp.Integer,
    "Float": sp.Float,
    "Rational": sp.Rational,
    "Pow": sp.Pow,
    "Mul": sp.Mul,
    "Add": sp.Add,
}


def _make_base_local_dict(named_funcs: dict):
    local = {
        "x": X_SYM,
        "y": Y_SYM,
        "z": Z_SYM,
        "t": T_SYM,
        "theta": THETA_SYM,
        "r": R_SYM,
        "u": U_SYM,
        "v": V_SYM,
        "e": sp.E,
        "pi": sp.pi,
        "oo": sp.oo,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "asin": sp.asin,
        "acos": sp.acos,
        "atan": sp.atan,
        "sinh": sp.sinh,
        "cosh": sp.cosh,
        "tanh": sp.tanh,
        "sec": sp.sec,
        "csc": sp.csc,
        "cot": sp.cot,
        "exp": sp.exp,
        "ln": sp.log,
        "log": lambda a, b=10: sp.log(a, b),
        "sqrt": sp.sqrt,
        "nthroot": nthroot,
        "factorial": sp.factorial,
        "gamma": sp.gamma,
        "abs": sp.Abs,
        "Abs": sp.Abs,
        "floor": sp.floor,
        "ceiling": sp.ceiling,
        "sign": sp.sign,
        "Sum": sp.Sum,
        "Product": sp.Product,
        "Integral": sp.Integral,
        "Derivative": sp.Derivative,
        "ddx": lambda expr: sp.Derivative(
            expr.replace(nthroot, lambda a, n: a ** (sp.Integer(1) / n)), X_SYM
        ),
        "diff": lambda expr, var=X_SYM: sp.Derivative(
            expr.replace(nthroot, lambda a, n: a ** (sp.Integer(1) / n)), var
        ),
    }
    for fname in named_funcs:
        local[fname] = _make_placeholder_func(fname, 0)
        for order in (1, 2, 3):
            local[f"__deriv{order}_{fname}"] = _make_placeholder_func(fname, order)
    return local


def _parse_symbolic(expr_str: str, named_funcs: dict):
    local = _make_base_local_dict(named_funcs)
    return parse_expr(
        expr_str,
        local_dict=local,
        global_dict=dict(SAFE_SYMPY_GLOBALS),
        transformations=TRANSFORMATIONS,
    )


def split_top_level_comma(s: str):
    if not (s.startswith("(") and s.endswith(")")):
        return None
    inner = s[1:-1]
    depth = 0
    split_idx = -1
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return None
        elif ch == "," and depth == 0:
            if split_idx != -1:
                return None
            split_idx = i
    if split_idx == -1 or depth != 0:
        return None
    return inner[:split_idx].strip(), inner[split_idx + 1 :].strip()


_DOMAIN_OP_TOKENS = ("<=", ">=", "<", ">", "=", "\\le", "\\leq", "\\ge", "\\geq", "≤", "≥")


def _find_matching_brace(text: str, open_pos: int, escaped: bool) -> tuple[int, int] | None:
    n = len(text)
    if escaped:
        depth = 1
        i = open_pos + 1
        while i < n:
            if text.startswith("\\left\\{", i):
                depth += 1
                i += 7
                continue
            if text.startswith("\\right\\}", i):
                depth -= 1
                if depth == 0:
                    return i, i + 8
                i += 8
                continue
            if text.startswith("\\{", i):
                depth += 1
                i += 2
                continue
            if text.startswith("\\}", i):
                depth -= 1
                if depth == 0:
                    return i, i + 2
                i += 2
                continue
            i += 1
        return None
    else:
        depth = 1
        i = open_pos + 1
        while i < n:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return i, i + 1
            i += 1
        return None


def _is_command_brace(prefix: str) -> bool:
    p = prefix.rstrip()
    if not p:
        return False
    if p[-1] in ("^", "_"):
        return True
    if re.search(r"\\(?:frac|sqrt|operatorname|mathrm|text|mathbf|left|right)\s*(?:\[[^\]]*\])?$", p):
        return True
    if p[-1] == "}":
        depth = 1
        i = len(p) - 2
        while i >= 0:
            if p[i] == "}":
                depth += 1
            elif p[i] == "{":
                depth -= 1
                if depth == 0:
                    before = p[:i].rstrip()
                    if re.search(r"\\frac$", before):
                        return True
                    break
            i -= 1
    return False


def _split_top_level_char(s: str, sep: str) -> list[str]:
    parts = []
    depth_p = depth_b = depth_s = 0
    start = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth_p += 1
        elif ch == ")":
            depth_p = max(0, depth_p - 1)
        elif ch == "{":
            depth_b += 1
        elif ch == "}":
            depth_b = max(0, depth_b - 1)
        elif ch == "[":
            depth_s += 1
        elif ch == "]":
            depth_s = max(0, depth_s - 1)
        elif ch == sep and depth_p == 0 and depth_b == 0 and depth_s == 0:
            parts.append(s[start:i].strip())
            start = i + 1
    parts.append(s[start:].strip())
    return parts


def extract_domain_restrictions(raw: str) -> tuple[str, list[str]]:
    s = raw.strip()
    if not s:
        return s, []

    conditions: list[str] = []

    while True:
        s_r = s.rstrip()
        if not s_r:
            break

        end_kind = None
        if s_r.endswith("\\right\\}"):
            end_kind = "escaped"
            search_end = len(s_r) - 8
        elif s_r.endswith("\\}"):
            end_kind = "escaped"
            search_end = len(s_r) - 2
        elif s_r.endswith("}"):
            end_kind = "plain"
            search_end = len(s_r) - 1
        else:
            break

        open_start = -1
        inner_start = -1
        if end_kind == "escaped":
            depth = 1
            i = search_end - 1
            while i >= 0:
                if i >= 7 and s_r[i - 7 : i + 1] == "\\right\\}":
                    depth += 1
                    i -= 8
                    continue
                if i >= 1 and s_r[i - 1 : i + 1] == "\\}":
                    depth += 1
                    i -= 2
                    continue
                if i >= 6 and s_r[i - 6 : i + 1] == "\\left\\{":
                    depth -= 1
                    if depth == 0:
                        open_start = i - 6
                        inner_start = i + 1
                        break
                    i -= 7
                    continue
                if i >= 1 and s_r[i - 1 : i + 1] == "\\{":
                    depth -= 1
                    if depth == 0:
                        open_start = i - 1
                        inner_start = i + 1
                        break
                    i -= 2
                    continue
                i -= 1
        else:
            depth = 1
            i = search_end - 1
            while i >= 0:
                if s_r[i] == "}":
                    depth += 1
                elif s_r[i] == "{":
                    depth -= 1
                    if depth == 0:
                        open_start = i
                        inner_start = i + 1
                        break
                i -= 1

        if open_start < 0:
            break

        prefix = s_r[:open_start]
        inner = s_r[inner_start:search_end].strip()

        if ":" in inner:
            break

        if end_kind == "plain" and _is_command_brace(prefix):
            break

        if not prefix.strip() or not any(tok in inner for tok in _DOMAIN_OP_TOKENS):
            break

        for sub_cond in _split_top_level_char(inner, ","):
            if sub_cond:
                conditions.insert(0, sub_cond)
        s = prefix.rstrip()

    return s, conditions


def parse_single_condition_chain(cond_raw: str, named_funcs: dict) -> list[tuple[sp.Expr, str, sp.Expr]]:
    cleaned = preprocess_latex(cond_raw)
    if not cleaned or cleaned == "__INCOMPLETE__":
        return []

    tokens: list[str] = []
    ops: list[str] = []
    depth = 0
    start = 0
    i = 0
    n = len(cleaned)
    while i < n:
        ch = cleaned[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            if cleaned.startswith("<=", i) or cleaned.startswith(">=", i):
                tokens.append(cleaned[start:i].strip())
                ops.append(cleaned[i : i + 2])
                i += 2
                start = i
                continue
            if ch in ("<", ">"):
                tokens.append(cleaned[start:i].strip())
                ops.append(ch)
                i += 1
                start = i
                continue
        i += 1
    tokens.append(cleaned[start:].strip())

    if not ops or any(not t for t in tokens):
        return []

    parsed = [_parse_symbolic(t, named_funcs) for t in tokens]
    chain = []
    for idx, op in enumerate(ops):
        chain.append((parsed[idx], op, parsed[idx + 1]))
    return chain


def parse_domain_conditions(cond_strs: list[str], named_funcs: dict) -> list[tuple[sp.Expr, str, sp.Expr]]:
    all_chains: list[tuple[sp.Expr, str, sp.Expr]] = []
    for cs in cond_strs:
        all_chains.extend(parse_single_condition_chain(cs, named_funcs))
    return all_chains


def parse_piecewise_rhs(raw_rhs: str, named_funcs: dict) -> sp.Expr | None:
    s = raw_rhs.strip()
    inner = None
    if s.startswith("\\left\\{") and s.endswith("\\right\\}"):
        inner = s[7:-8].strip()
    elif s.startswith("\\{") and s.endswith("\\}"):
        inner = s[2:-2].strip()
    elif s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
    if inner is None or ":" not in inner:
        return None

    branches = _split_top_level_char(inner, ",")
    pw_args = []
    for br in branches:
        if not br:
            continue
        if ":" in br:
            c_raw, e_raw = br.split(":", 1)
            chain = parse_single_condition_chain(c_raw.strip(), named_funcs)
            if not chain:
                return None
            e_clean = preprocess_latex(e_raw.strip())
            if not e_clean or e_clean == "__INCOMPLETE__":
                return None
            e_sym = _parse_symbolic(e_clean, named_funcs)
            rel_list = []
            for lhs, op, rhs in chain:
                if op == "<":
                    rel_list.append(sp.Lt(lhs, rhs))
                elif op == "<=":
                    rel_list.append(sp.Le(lhs, rhs))
                elif op == ">":
                    rel_list.append(sp.Gt(lhs, rhs))
                else:
                    rel_list.append(sp.Ge(lhs, rhs))
            cond_sym = rel_list[0] if len(rel_list) == 1 else sp.And(*rel_list)
            pw_args.append((e_sym, cond_sym))
        else:
            e_clean = preprocess_latex(br.strip())
            if not e_clean or e_clean == "__INCOMPLETE__":
                return None
            pw_args.append((_parse_symbolic(e_clean, named_funcs), True))

    return sp.Piecewise(*pw_args) if pw_args else None


def _normalize_brackets(raw: str) -> str:
    return (
        raw.strip()
        .replace("\\left[", "[")
        .replace("\\right]", "]")
        .replace("\\ldots", "...")
        .replace("\\cdots", "...")
        .replace("…", "...")
    )


def parse_list_definition(raw: str, max_items: int = 30) -> tuple[str, list[float]] | None:
    s = _normalize_brackets(raw)
    m = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*=\s*\[(.*)\]$", s)
    if not m:
        return None
    name, inner = m.group(1), m.group(2).strip()
    if name in RESERVED_SYMS or name in BUILTIN_FUNC_NAMES or not inner:
        return None

    def _eval_num(tok: str) -> float | None:
        c = preprocess_latex(tok)
        if not c or c == "__INCOMPLETE__":
            return None
        ex = _parse_symbolic(c, {})
        if ex.free_symbols:
            return None
        v = float(ex.evalf())
        return v if np.isfinite(v) else None

    if "..." in inner or ".." in inner:
        parts = [p.strip() for p in _split_top_level_char(inner, ",") if p.strip()]
        if len(parts) == 1:
            sep = "..." if "..." in parts[0] else ".."
            ab = parts[0].split(sep, 1)
            v0, v1 = _eval_num(ab[0]), _eval_num(ab[1])
            if v0 is None or v1 is None:
                return None
            step = 1.0 if v1 >= v0 else -1.0
        elif len(parts) == 3 and parts[1] in ("...", ".."):
            v0, v1 = _eval_num(parts[0]), _eval_num(parts[2])
            if v0 is None or v1 is None:
                return None
            step = 1.0 if v1 >= v0 else -1.0
        elif len(parts) == 4 and parts[2] in ("...", ".."):
            v0, v_next, v1 = _eval_num(parts[0]), _eval_num(parts[1]), _eval_num(parts[3])
            if v0 is None or v_next is None or v1 is None:
                return None
            step = v_next - v0
            if abs(step) < 1e-12:
                return None
        else:
            return None

        vals: list[float] = []
        cur = v0
        eps = abs(step) * 1e-6 + 1e-12
        for _ in range(max_items):
            if (step > 0 and cur > v1 + eps) or (step < 0 and cur < v1 - eps):
                break
            vals.append(float(f"{cur:.7g}"))
            cur += step
        return (name, vals) if vals else None

    parts = [p.strip() for p in _split_top_level_char(inner, ",") if p.strip()]
    if not parts:
        return None
    vals = []
    for tok in parts[:max_items]:
        v = _eval_num(tok)
        if v is None:
            return None
        vals.append(float(f"{v:.7g}"))
    return (name, vals) if vals else None


def parse_ode_equation(raw: str) -> str | None:
    s = raw.strip().replace("′", "'").replace("’", "'").replace("^{\\prime}", "'").replace("\\prime", "'")
    s = s.replace("\\mathrm{d}", "d").replace("\\differentialD", "d")
    patterns = (
        r"^y\s*'\s*=\s*(.+)$",
        r"^\\frac\s*\{\s*d\s*y\s*\}\s*\{\s*d\s*x\s*\}\s*=\s*(.+)$",
        r"^d\s*y\s*/\s*d\s*x\s*=\s*(.+)$",
    )
    for pat in patterns:
        m = re.match(pat, s)
        if m:
            rhs = m.group(1).strip()
            if rhs and not any(op in rhs for op in ("<", ">", "=")):
                return rhs
    return None


def parse_surface_3d(raw: str) -> str | None:
    s = raw.strip()
    m = re.match(r"^z\s*=\s*(.+)$", s)
    if not m:
        return None
    rhs = m.group(1).strip()
    if not rhs or any(op in rhs for op in ("<", ">", "=")):
        return None
    return rhs


def parse_regression_expr(raw: str) -> tuple[int, str] | None:
    s = raw.strip()
    s = s.replace("\\sim", "~").replace("\\approx", "~").replace("∼", "~")
    if "~" not in s:
        return None
    lhs, rhs = s.split("~", 1)
    lhs_clean = re.sub(r"\s+", "", lhs).replace("{", "").replace("}", "")
    m = re.match(r"^y_?(\d+)$", lhs_clean)
    if not m:
        return None
    tbl_idx = int(m.group(1))
    rhs_norm = re.sub(rf"x_\{{\s*{tbl_idx}\s*\}}", "x", rhs)
    rhs_norm = re.sub(rf"x_{tbl_idx}\b", "x", rhs_norm)
    rhs_norm = re.sub(rf"\bx{tbl_idx}\b", "x", rhs_norm)
    return tbl_idx, rhs_norm.strip()


def split_top_level_tuple(s: str) -> list[str] | None:
    if not (s.startswith("(") and s.endswith(")")):
        return None
    inner = s[1:-1]
    parts = _split_top_level_char(inner, ",")
    if len(parts) not in (2, 3) or any(not p for p in parts):
        return None
    return parts


def _parse_bracket_list_inner(inner: str, max_items: int = 30) -> list[float] | None:
    inner = inner.strip()
    if not inner:
        return None

    def _eval_num(tok: str) -> float | None:
        c = preprocess_latex(tok)
        if not c or c == "__INCOMPLETE__":
            return None
        ex = _parse_symbolic(c, {})
        if ex.free_symbols:
            return None
        v = float(ex.evalf())
        return v if np.isfinite(v) else None

    if "..." in inner or ".." in inner:
        parts = [p.strip() for p in _split_top_level_char(inner, ",") if p.strip()]
        if len(parts) == 1:
            sep = "..." if "..." in parts[0] else ".."
            ab = parts[0].split(sep, 1)
            v0, v1 = _eval_num(ab[0]), _eval_num(ab[1])
            if v0 is None or v1 is None:
                return None
            step = 1.0 if v1 >= v0 else -1.0
        elif len(parts) == 3 and parts[1] in ("...", ".."):
            v0, v1 = _eval_num(parts[0]), _eval_num(parts[2])
            if v0 is None or v1 is None:
                return None
            step = 1.0 if v1 >= v0 else -1.0
        elif len(parts) == 4 and parts[2] in ("...", ".."):
            v0, v_next, v1 = _eval_num(parts[0]), _eval_num(parts[1]), _eval_num(parts[3])
            if v0 is None or v_next is None or v1 is None:
                return None
            step = v_next - v0
            if abs(step) < 1e-12:
                return None
        else:
            return None

        vals: list[float] = []
        cur = v0
        eps = abs(step) * 1e-6 + 1e-12
        for _ in range(max_items):
            if (step > 0 and cur > v1 + eps) or (step < 0 and cur < v1 - eps):
                break
            vals.append(float(f"{cur:.7g}"))
            cur += step
        return vals if vals else None

    parts = [p.strip() for p in _split_top_level_char(inner, ",") if p.strip()]
    if not parts:
        return None
    vals = []
    for tok in parts[:max_items]:
        v = _eval_num(tok)
        if v is None:
            return None
        vals.append(float(f"{v:.7g}"))
    return vals if vals else None


def extract_inline_lists(raw: str, max_items: int = 30) -> tuple[str, dict[str, list[float]]]:
    s = _normalize_brackets(raw)
    if "[" not in s:
        return raw, {}

    inline_lists: dict[str, list[float]] = {}
    out = []
    i = 0
    n = len(s)
    counter = 0

    while i < n:
        if s[i] == "[":
            prefix = "".join(out).rstrip()
            if prefix.endswith("\\sqrt"):
                out.append(s[i])
                i += 1
                continue
            res = _read_balanced(s, i, "[", "]")
            if res is not None:
                inner, end_pos = res
                if "," in inner or ".." in inner:
                    vals = _parse_bracket_list_inner(inner, max_items=max_items)
                    if vals is not None:
                        lname = f"__ilist{counter}"
                        counter += 1
                        inline_lists[lname] = vals
                        out.append(f" {lname} ")
                        i = end_pos
                        continue
        out.append(s[i])
        i += 1

    if not inline_lists:
        return raw, {}
    return "".join(out), inline_lists


def extract_z_plane_restriction(domain_strs: list[str], named_funcs: dict) -> tuple[sp.Expr | None, list[str]]:
    if not domain_strs:
        return None, []
    z_expr = None
    remaining: list[str] = []
    for ds in domain_strs:
        cleaned = preprocess_latex(ds)
        if "=" in cleaned and not any(op in cleaned for op in ("<=", ">=", "<", ">")):
            lhs_s, rhs_s = cleaned.split("=", 1)
            try:
                lhs_e = _parse_symbolic(lhs_s, named_funcs)
                rhs_e = _parse_symbolic(rhs_s, named_funcs)
                if lhs_e == Z_SYM and Z_SYM not in rhs_e.free_symbols:
                    z_expr = rhs_e
                    continue
                if rhs_e == Z_SYM and Z_SYM not in lhs_e.free_symbols:
                    z_expr = lhs_e
                    continue
            except Exception:
                pass
        remaining.append(ds)
    return z_expr, remaining

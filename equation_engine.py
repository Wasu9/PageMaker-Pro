"""Unicode-first equation helpers for NEET/JEE paper production.

Keeps ordinary mathematical notation editable/copyable as Unicode. Structured
math objects can later be rendered visually without changing the stored text.
"""
import re

SYMBOLS = {
    "alpha":"α", "beta":"β", "gamma":"γ", "delta":"δ", "theta":"θ",
    "lambda":"λ", "mu":"μ", "pi":"π", "sigma":"σ", "phi":"φ",
    "omega":"ω", "Omega":"Ω", "Delta":"Δ", "Sigma":"Σ",
    "sqrt":"√", "cuberoot":"∛", "infinity":"∞", "sum":"∑",
    "integral":"∫", "partial":"∂", "nabla":"∇", "plusminus":"±",
    "times":"×", "divide":"÷", "neq":"≠", "approx":"≈",
    "le":"≤", "ge":"≥", "proportional":"∝", "rightarrow":"→",
    "implies":"⇒", "iff":"⇔", "therefore":"∴", "angle":"∠",
}

_SUP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SUB = str.maketrans("0123456789+-=()n", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙ")


def symbol(name):
    return SYMBOLS.get(name, name)


def superscript(value):
    return str(value).translate(_SUP)


def subscript(value):
    return str(value).translate(_SUB)


def fraction(numerator, denominator):
    return f"{numerator}⁄{denominator}"


def normalize_common(text):
    for name, value in sorted(SYMBOLS.items(), key=lambda x: -len(x[0])):
        text = re.sub(r"\\" + re.escape(name) + r"\b", value, text)
    return text


def chemistry(formula):
    """Convert simple chemical digits after element symbols to subscripts."""
    return re.sub(r"(?<=[A-Za-z\)])([0-9]+)", lambda m: subscript(m.group(1)), formula)

"""Core parsers for :mod:`numparse`."""

from __future__ import annotations

import math
import re
from typing import Any, Optional, Tuple, Union

__version__ = "1.0.0"

Number = Union[int, float]


class NumParseError(ValueError):
    """Raised on malformed numeric input.

    Subclasses :class:`ValueError` so existing ``except ValueError`` handlers
    continue to catch it.
    """


# Sentinel used to distinguish "no default supplied" from ``default=None``.
class _Missing:
    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "<missing>"


_MISSING: Any = _Missing()


def _require_str(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a str, got {type(value).__name__}"
        )
    return value


# Strip currency symbols from either end.
_CURRENCY_CHARS = "$€£¥₹₽₩฿"
_CURRENCY_RE = re.compile(
    "^[" + re.escape(_CURRENCY_CHARS) + r"]\s*|\s*[" + re.escape(_CURRENCY_CHARS) + r"]$"
)


def _strip_wrapper(text: str) -> str:
    """Remove surrounding whitespace and a single currency symbol."""
    stripped = text.strip()
    return _CURRENCY_RE.sub("", stripped).strip()


def _normalise_sign(text: str) -> str:
    """Replace the Unicode MINUS SIGN with ASCII ``-``."""
    return text.replace("\u2212", "-")


def _parse_digit_separators(core: str) -> str:
    """Return *core* with thousand separators removed, or raise.

    Accepted digit-separator conventions (one per number):

    * commas:     ``1,234,567``
    * spaces:     ``1 234 567``
    * underscores: ``1_234_567``

    Rules:

    * The separators must group the integer portion into runs of exactly 3 digits
      (except for the leading group, which can be 1–3 digits).
    * Separators are stripped entirely; decimals and exponents are left alone.
    """
    # Peel off an optional exponent first so the separator check only
    # inspects the mantissa.
    mantissa, exp_sep, exponent = _split_exponent(core)

    # Split mantissa at the decimal point.
    if "." in mantissa:
        int_part, _, frac_part = mantissa.partition(".")
    else:
        int_part, frac_part = mantissa, ""

    # Pull sign off the integer part.
    sign = ""
    if int_part and int_part[0] in "+-":
        sign, int_part = int_part[0], int_part[1:]

    # Detect which separator family (if any) is used.
    separators_used = {c for c in int_part if c in ",_ "}
    if len(separators_used) > 1:
        raise NumParseError(f"mixed digit separators in {core!r}")

    cleaned_int: str
    if not separators_used:
        cleaned_int = int_part
    else:
        sep = separators_used.pop()
        groups = int_part.split(sep)
        if any(not g for g in groups):
            raise NumParseError(f"empty digit group in {core!r}")
        head = groups[0]
        tail = groups[1:]
        if not head.isdigit() or len(head) > 3 or len(head) < 1:
            raise NumParseError(f"invalid digit grouping in {core!r}")
        for group in tail:
            if not group.isdigit() or len(group) != 3:
                raise NumParseError(f"invalid digit grouping in {core!r}")
        cleaned_int = "".join(groups)

    if frac_part and not frac_part.isdigit():
        raise NumParseError(f"invalid fractional part in {core!r}")

    result = sign + cleaned_int
    if "." in mantissa:
        result += "." + frac_part
    if exp_sep:
        result += exp_sep + exponent
    return result


def _split_exponent(text: str) -> Tuple[str, str, str]:
    """Split *text* into ``(mantissa, separator, exponent)``.

    If there is no ``e``/``E`` separator the latter two fields are ``""``.
    """
    for i, ch in enumerate(text):
        if ch in "eE":
            return text[:i], ch, text[i + 1 :]
    return text, "", ""


# Magnitude suffix → multiplier for :func:`parse`. Ordered by length so the
# longer forms match first when we search.
_MAGNITUDE = {
    "k": 10**3,
    "K": 10**3,
    "M": 10**6,
    "B": 10**9,
    "G": 10**9,
    "T": 10**12,
}


def _peel_magnitude_suffix(text: str) -> Tuple[str, int]:
    """Return ``(core_number, multiplier)`` after peeling a magnitude suffix.

    If *text* does not end in a recognised single-letter suffix, returns
    ``(text, 1)``.

    The caller is expected to have already stripped currency symbols and
    whitespace from both ends. A single space between number and suffix
    (``"2.5 M"``) is tolerated.
    """
    if not text:  // placeholder; the real body is below
        return text, 1
    last = text[-1]
    if last not in _MAGNITUDE:
        return text, 1
    core = text[:-1].rstrip()
    if not core or core in "+-":
        raise NumParseError("magnitude suffix with no digits")
    return core, _MAGNITUDE[last]

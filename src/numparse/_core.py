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
    if not text:  # pragma: no cover - callers never pass empty after strip
        return text, 1
    last = text[-1]
    if last not in _MAGNITUDE:
        return text, 1
    core = text[:-1].rstrip()
    if not core or core in "+-":
        raise NumParseError("magnitude suffix with no digits")
    return core, _MAGNITUDE[last]


def _clean_core_to_number(core: str) -> Number:
    """Parse a cleaned numeric core (no suffixes, no currency) into int/float.

    The core may still contain thousand separators.
    """
    normalised = _parse_digit_separators(core)

    # Reject inf/nan at this layer — those belong to :func:`parse_float`.
    # :func:`_parse_core` already handles this earlier, so this branch is
    # defensive for any direct callers (e.g. :func:`parse_bytes`).
    lowered = normalised.lstrip("+-").lower()
    if lowered in {"inf", "infinity", "nan"}:  # pragma: no cover - guarded upstream
        raise NumParseError(f"not a finite number: {core!r}")

    # Prefer int parsing when there's no decimal or exponent.
    if "." not in normalised and "e" not in normalised and "E" not in normalised:
        try:
            return int(normalised)
        except ValueError as exc:
            raise NumParseError(f"cannot parse {core!r}: {exc}") from exc
    try:
        return float(normalised)
    except ValueError as exc:  # pragma: no cover - separator cleaner rejects these first
        raise NumParseError(f"cannot parse {core!r}: {exc}") from exc


def _parse_core(text: str, *, allow_infnan: bool = False) -> Number:
    """Shared pipeline used by :func:`parse`, :func:`parse_int`, :func:`parse_float`.

    Handles currency wrapping, unicode minus, magnitude suffixes, and the
    digit-separator dance. Raises :class:`NumParseError` on failure.
    """
    inner = _strip_wrapper(text)
    inner = _normalise_sign(inner)
    if not inner:
        raise NumParseError("empty input")

    # `inf` / `nan` are only valid when the caller opted in.
    lowered = inner.lstrip("+-").lower()
    if lowered in {"inf", "infinity", "nan"}:
        if not allow_infnan:
            raise NumParseError(f"not a finite number: {text!r}")
        return float(inner)

    core, multiplier = _peel_magnitude_suffix(inner)
    base = _clean_core_to_number(core)
    if multiplier == 1:
        return base
    scaled = base * multiplier
    if isinstance(base, int) and isinstance(scaled, int):
        return scaled
    # Collapse to int if scaled is whole (`2k` → 2000 not 2000.0).
    if isinstance(scaled, float) and scaled.is_integer():
        return int(scaled)
    return scaled


def _with_default(func, default: Any, *args: Any, **kwargs: Any) -> Any:
    """Run *func*; if it raises :class:`NumParseError`, return *default* if given."""
    try:
        return func(*args, **kwargs)
    except NumParseError:
        if default is _MISSING:
            raise
        return default


# --- Public API ------------------------------------------------------------


def parse(text: str, *, default: Any = _MISSING) -> Any:
    """Parse a loose numeric string into an ``int`` or ``float``.

    Accepts:

    * plain integers and decimals
    * leading sign (``+``, ``-``, or Unicode ``\u2212``)
    * thousand separators: ``,``, space, ``_``
    * scientific notation: ``1.5e3``, ``2E-6``
    * magnitude suffixes: ``k``/``K``, ``M``, ``G``/``B``, ``T``
      (with or without a single space before)
    * currency symbols at either end: ``$ € £ ¥ ₹ ₽ ₩ ฿``

    Returns:
        ``int`` when the result is a whole number; ``float`` otherwise.

    Raises:
        TypeError: if *text* is not a string.
        NumParseError: on malformed input (when no *default* supplied).
    """
    _require_str(text, "text")
    return _with_default(_parse_core, default, text, allow_infnan=False)


def parse_int(text: str, *, default: Any = _MISSING) -> Any:
    """Parse *text* into an ``int``.

    Accepts the same syntax as :func:`parse`, but rejects any input that
    does not ultimately resolve to a whole-number value.

    Raises:
        TypeError / NumParseError as for :func:`parse`.
    """
    _require_str(text, "text")

    def _do() -> int:
        value = _parse_core(text, allow_infnan=False)
        if isinstance(value, int):
            return value
        if value.is_integer():
            return int(value)
        raise NumParseError(f"not an integer: {text!r}")

    return _with_default(_do, default)


def parse_float(text: str, *, default: Any = _MISSING) -> Any:
    """Parse *text* into a ``float`` (``inf``/``nan`` allowed).

    Raises:
        TypeError / NumParseError as for :func:`parse`.
    """
    _require_str(text, "text")

    def _do() -> float:
        value = _parse_core(text, allow_infnan=True)
        return float(value)

    return _with_default(_do, default)


# --- Bytes -----------------------------------------------------------------


_BYTE_UNITS = {
    # Decimal
    "": 1,
    "B": 1,
    "KB": 10**3,
    "MB": 10**6,
    "GB": 10**9,
    "TB": 10**12,
    "PB": 10**15,
    "EB": 10**18,
    # Binary
    "KIB": 1024,
    "MIB": 1024**2,
    "GIB": 1024**3,
    "TIB": 1024**4,
    "PIB": 1024**5,
    "EIB": 1024**6,
}

_BYTES_RE = re.compile(
    r"^(?P<num>[0-9][0-9_,. ]*(?:[eE][+\-]?\d+)?)\s*(?P<unit>[a-zA-Z]*)$"
)


def parse_bytes(text: str, *, default: Any = _MISSING) -> Any:
    """Parse a byte-size string into an integer number of bytes.

    ``KB``, ``MB``, … use decimal multipliers (powers of 1000).
    ``KiB``, ``MiB``, … use binary multipliers (powers of 1024).
    A bare ``B`` or no suffix treats the number as raw bytes.

    Suffix matching is case-insensitive — ``kb``, ``Kb``, ``KB`` all work.

    Fractional sizes are accepted (``"1.5 KB"`` → ``1500``) but the result
    is always an ``int``; anything past the final byte is truncated with
    :func:`math.floor`.

    Raises:
        TypeError / NumParseError as for :func:`parse`.
    """
    _require_str(text, "text")

    def _do() -> int:
        inner = _strip_wrapper(text)
        inner = _normalise_sign(inner)
        if not inner:
            raise NumParseError("empty input")
        if inner.startswith("-"):
            raise NumParseError("byte size cannot be negative")
        match = _BYTES_RE.match(inner)
        if not match:
            raise NumParseError(f"not a byte size: {text!r}")
        unit = match.group("unit").upper()
        if unit not in _BYTE_UNITS:
            raise NumParseError(f"unknown byte-size unit {unit!r}")
        multiplier = _BYTE_UNITS[unit]
        number = _clean_core_to_number(match.group("num").strip())
        if number < 0:  # pragma: no cover - regex forbids leading sign
            raise NumParseError("byte size cannot be negative")
        total = number * multiplier
        if isinstance(total, float):
            total = math.floor(total)
        return int(total)

    return _with_default(_do, default)


# --- Duration --------------------------------------------------------------


_DURATION_UNITS = {
    "ns": 1e-9,
    "us": 1e-6,
    "µs": 1e-6,  # U+00B5 micro sign
    "μs": 1e-6,  # U+03BC greek small letter mu
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "w": 7 * 86400.0,
}

# Ordered longest-first so e.g. ``ms`` matches before ``m``.
_DURATION_UNIT_KEYS = sorted(_DURATION_UNITS.keys(), key=len, reverse=True)
_DURATION_COMPONENT_RE = re.compile(
    r"([+\-]?\d+(?:\.\d+)?)\s*(" + "|".join(re.escape(k) for k in _DURATION_UNIT_KEYS) + r")"
)


def parse_duration(text: str, *, default: Any = _MISSING) -> Any:
    """Parse a duration like ``"1h30m"`` or ``"250ms"`` into seconds.

    Recognised unit suffixes (case-sensitive):

    ===== ==============
    Unit  Meaning
    ===== ==============
    ns    nanoseconds
    us    microseconds
    µs    microseconds (U+00B5)
    μs    microseconds (U+03BC)
    ms    milliseconds
    s     seconds
    m     minutes
    h     hours
    d     days
    w     weeks
    ===== ==============

    Components may be combined with or without internal whitespace
    (``"1h 30m"`` and ``"1h30m"`` are both valid). A bare number with no
    suffix is treated as seconds.

    Raises:
        TypeError / NumParseError as for :func:`parse`.
    """
    _require_str(text, "text")

    def _do() -> float:
        inner = _strip_wrapper(text).replace(" ", "")
        inner = _normalise_sign(inner)
        if not inner:
            raise NumParseError("empty input")

        # Fast path: bare number → seconds.
        try:
            return float(_clean_core_to_number(inner))
        except NumParseError:
            pass

        total = 0.0
        seen: set[str] = set()
        position = 0
        sign = 1.0
        if inner[0] in "+-":
            if inner[0] == "-":
                sign = -1.0
            inner = inner[1:]
        if not inner:
            raise NumParseError("empty duration")

        while position < len(inner):
            match = _DURATION_COMPONENT_RE.match(inner, position)
            if not match:
                raise NumParseError(f"bad duration component in {text!r}")
            number_str, unit = match.group(1), match.group(2)
            if unit in seen:
                raise NumParseError(f"duplicate duration unit {unit!r}")
            seen.add(unit)
            total += float(number_str) * _DURATION_UNITS[unit]
            position = match.end()
        if position != len(inner):  # pragma: no cover - component regex would reject earlier
            raise NumParseError(f"trailing junk in duration {text!r}")
        return sign * total

    return _with_default(_do, default)


# --- Percent ---------------------------------------------------------------


def parse_percent(text: str, *, default: Any = _MISSING) -> Any:
    """Parse a percentage string into a plain fraction.

    ``"25%"`` → ``0.25``; ``"12.5%"`` → ``0.125``; ``"150%"`` → ``1.5``.

    A bare number (no ``%``) is treated as a percentage too, for
    convenience — ``"25"`` also yields ``0.25``.

    Raises:
        TypeError / NumParseError as for :func:`parse`.
    """
    _require_str(text, "text")

    def _do() -> float:
        inner = _strip_wrapper(text)
        if not inner:
            raise NumParseError("empty input")
        if inner.endswith("%"):
            inner = inner[:-1].rstrip()
        value = _parse_core(inner, allow_infnan=False)
        return float(value) / 100.0

    return _with_default(_do, default)

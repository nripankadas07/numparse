"""numparse — forgiving numeric string parsing.

Turn the messy numbers that humans write — ``"$1,234.56"``, ``"1.5k"``,
``"2 MiB"``, ``"1h30m"``, ``"12.5%"`` — into clean Python ``int``/``float``
values.

Public API:

* :func:`parse`            — smart parse; returns ``int`` for whole results, ``float`` otherwise.
* :func:`parse_int`        — integer-only parse.
* :func:`parse_float`      — float parse (allows ``inf`` / ``nan``).
* :func:`parse_bytes`      — byte sizes with KB/KiB/MB/MiB/… suffixes.
* :func:`parse_duration`   — durations with ns/us/ms/s/m/h/d/w suffixes, compoundable.
* :func:`parse_percent`    — ``"25%"`` → ``0.25``.
* :class:`NumParseError`   — raised on invalid input (subclass of ``ValueError``).

Every parser accepts an optional ``default=`` keyword. If supplied,
invalid input returns the default instead of raising.
"""

from __future__ import annotations

from ._core import (
    NumParseError,
    __version__,
    parse,
    parse_bytes,
    parse_duration,
    parse_float,
    parse_int,
    parse_percent,
)

__all__ = [
    "NumParseError",
    "__version__",
    "parse",
    "parse_bytes",
    "parse_duration",
    "parse_float",
    "parse_int",
    "parse_percent",
]

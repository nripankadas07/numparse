# numparse

Forgiving numeric-string parser. Turns the messy numbers that humans
write — `"$1,234.56"`, `"1.5k"`, `"2 MiB"`, `"1h30m"`, `"12.5%"` —
into clean Python `int` / `float` values. Zero runtime dependencies.

## Install

```bash
pip install numparse
```

Requires Python 3.8 or newer.

## Why not `int()` / `float()`?

Python's built-ins are strict: they reject thousand separators,
currency symbols, magnitude suffixes, byte sizes, and anything else
a human might type. `numparse` handles those without losing precision
or silently returning something wrong.

## Usage

```python
from numparse import (
    parse, parse_int, parse_float,
    parse_bytes, parse_duration, parse_percent,
)

parse("$1,234.56")      # 1234.56
parse("1.5k")            # 1500
parse("−3")              # -3  (Unicode minus)
parse("1 234 567")       # 1234567
parse("2.5 M")           # 2500000

parse_int("1.5k")        # 1500  (fractional suffix ok, final value integral)
parse_float("inf")       # inf
parse_float("nan")       # nan

parse_bytes("1 KB")      # 1000
parse_bytes("1 KiB")     # 1024
parse_bytes("1.5 GiB")   # 1610612736

parse_duration("1h30m")  # 5400.0
parse_duration("250ms")  # 0.25
parse_duration("2d 3h")  # 183600.0

parse_percent("12.5%")   # 0.125
parse_percent("150%")    # 1.5
```

### Non-raising mode

Every function accepts an optional `default=` keyword. If parsing
fails, the default is returned instead of raising:

```python
parse("not a number", default=0)   # 0
parse_bytes("oops", default=None)  # None
```

## API reference

### `parse(text, *, default=...) -> int | float`

Smart parse. Accepts:

- plain integers and decimals
- leading sign: `+`, `-`, or Unicode `−` (U+2212)
- thousand separators: `,`, space, `_` (consistent within one number)
- scientific notation: `1.5e3`, `2E-6`
- magnitude suffixes: `k`/`K`, `M`, `G`/`B` (billion), `T` (trillion),
  with an optional space before the letter
- currency symbols at either end: `$ € £ ¥ ₹ ₽ ₩ ฿`

Returns `int` when the result is whole; `float` otherwise. `inf`
and `nan` are **not** accepted here; use `parse_float` instead.

### `parse_int(text, *, default=...) -> int`

Integer-only parse. Accepts the same syntax as `parse`, but raises
`NumParseError` if the value does not resolve to a whole integer.

### `parse_float(text, *, default=...) -> float`

Float parse. Always returns a `float`; accepts `inf`, `-inf`, `nan`.

### `parse_bytes(text, *, default=...) -> int`

Parses byte-size strings. Suffixes:

| Suffix  | Multiplier       |
| ------- | ---------------- |
| `B` / `` | 1               |
| `KB`    | 1 000            |
| `MB`    | 1 000 000        |
| `GB`    | 1 000 000 000    |
| `TB`    | 10^12            |
| `PB`    | 10^15            |
| `EB`    | 10^18            |
| `KiB`   | 1 024            |
| `MiB`   | 1 024^2          |
| `GiB`   | 1 024^3          |
| `TiB`   | 1 024^4          |
| `PiB`   | 1 024^5          |
| `EiB`   | 1 024^6          |

Suffix matching is case-insensitive. Fractional sizes are accepted and
floored to the nearest byte.

### `parse_duration(text, *, default=...) -> float`

Returns seconds (`float`). Unit suffixes: `ns`, `us`/`µs`/`μs`, `ms`,
`s`, `m`, `h`, `d`, `w`. Components can be combined (`1h30m` or
`1h 30m`). A bare number is treated as seconds.

### `parse_percent(text, *, default=...) -> float`

`"25%"` → `0.25`; `"150%"` → `1.5`. A bare number is treated as a
percentage too.

### `NumParseError`

Subclass of `ValueError` raised on malformed input when no `default`
was supplied.

## Non-goals

No locale-aware parsing (European `1.234,56` is not handled). No
fractions (`1/2`). No Roman numerals. No currency conversion.

## Running tests

```bash
pip install -e '.[dev]'
pytest
pytest --cov=numparse --cov-report=term-missing
```

## License

MIT.

"""Tests for :func:`parse_bytes`, :func:`parse_duration`, :func:`parse_percent`."""

from __future__ import annotations

import pytest

from numparse import (
    NumParseError,
    parse_bytes,
    parse_duration,
    parse_percent,
)


class TestParseBytes:
    def test_parse_bytes_raw_digits(self) -> None:
        assert parse_bytes("1024") == 1024

    def test_parse_bytes_with_b_suffix(self) -> None:
        assert parse_bytes("2048 B") == 2048

    def test_parse_bytes_kb_is_decimal_kilo(self) -> None:
        assert parse_bytes("1 KB") == 1000

    def test_parse_bytes_kib_is_binary(self) -> None:
        assert parse_bytes("1 KiB") == 1024

    def test_parse_bytes_mb(self) -> None:
        assert parse_bytes("1 MB") == 1_000_000

    def test_parse_bytes_mib(self) -> None:
        assert parse_bytes("1 MiB") == 1024 * 1024

    def test_parse_bytes_gib(self) -> None:
        assert parse_bytes("2 GiB") == 2 * 1024**3

    def test_parse_bytes_fractional_rounds_down(self) -> None:
        # 1.5 KB = 1500 bytes (integral).
        assert parse_bytes("1.5 KB") == 1500

    def test_parse_bytes_fractional_kib_truncates(self) -> None:
        # 1.5 KiB = 1536 bytes.
        assert parse_bytes("1.5 KiB") == 1536

    def test_parse_bytes_no_space(self) -> None:
        assert parse_bytes("1MB") == 1_000_000

    def test_parse_bytes_case_insensitive_bare(self) -> None:
        assert parse_bytes("1kb") == 1000
        assert parse_bytes("1Kb") == 1000

    def test_parse_bytes_ibi_prefix_case_sensitive(self) -> None:
        # "Ki" always uses the `i` — we require the binary suffix exactly.
        # Lowercase "kib" is still binary; we allow that convention.
        assert parse_bytes("1kib") == 1024

    def test_parse_bytes_negative_rejected(self) -> None:
        with pytest.raises(NumParseError):
            parse_bytes("-1 KB")

    def test_parse_bytes_empty_raises(self) -> None:
        with pytest.raises(NumParseError):
            parse_bytes("")

    def test_parse_bytes_unknown_suffix(self) -> None:
        with pytest.raises(NumParseError):
            parse_bytes("1 QB")

    def test_parse_bytes_default_on_failure(self) -> None:
        assert parse_bytes("bad", default=0) == 0

    def test_parse_bytes_rejects_non_string(self) -> None:
        with pytest.raises(TypeError):
            parse_bytes(1024)  # type: ignore[arg-type]


class TestParseDuration:
    def test_parse_duration_seconds_bare(self) -> None:
        assert parse_duration("42") == 42.0

    def test_parse_duration_seconds_with_s(self) -> None:
        assert parse_duration("30s") == 30.0

    def test_parse_duration_minutes(self) -> None:
        assert parse_duration("5m") == 300.0

    def test_parse_duration_hours(self) -> None:
        assert parse_duration("2h") == 7200.0

    def test_parse_duration_days(self) -> None:
        assert parse_duration("3d") == 3 * 86400.0

    def test_parse_duration_weeks(self) -> None:
        assert parse_duration("1w") == 7 * 86400.0

    def test_parse_duration_ms(self) -> None:
        assert parse_duration("500ms") == 0.5

    def test_parse_duration_us(self) -> None:
        assert parse_duration("250us") == pytest.approx(0.00025)

    def test_parse_duration_micro_sign(self) -> None:
        assert parse_duration("250µs") == pytest.approx(0.00025)

    def test_parse_duration_greek_mu(self) -> None:
        # U+03BC GREEK SMALL LETTER MU is common in code too.
        assert parse_duration("250μs") == pytest.approx(0.00025)

    def test_parse_duration_ns(self) -> None:
        assert parse_duration("1000ns") == pytest.approx(1e-6)

    def test_parse_duration_compound(self) -> None:
        assert parse_duration("1h30m") == 5400.0

    def test_parse_duration_compound_with_spaces(self) -> None:
        assert parse_duration("2d 3h 15m") == 2 * 86400 + 3 * 3600 + 15 * 60

    def test_parse_duration_compound_fractional(self) -> None:
        assert parse_duration("1.5h") == 5400.0

    def test_parse_duration_negative(self) -> None:
        assert parse_duration("-30s") == -30.0

    def test_parse_duration_empty_raises(self) -> None:
        with pytest.raises(NumParseError):
            parse_duration("")

    def test_parse_duration_unknown_unit(self) -> None:
        with pytest.raises(NumParseError):
            parse_duration("30fortnights")

    def test_parse_duration_default(self) -> None:
        assert parse_duration("bad", default=0.0) == 0.0

    def test_parse_duration_rejects_non_string(self) -> None:
        with pytest.raises(TypeError):
            parse_duration(30)  # type: ignore[arg-type]

    def test_parse_duration_repeated_unit_is_error(self) -> None:
        # "1h2h" is ambiguous — reject.
        with pytest.raises(NumParseError):
            parse_duration("1h2h")

    def test_parse_duration_bare_sign_is_empty(self) -> None:
        # A lone "-" with no digits must not be treated as zero.
        with pytest.raises(NumParseError):
            parse_duration("-")


class TestParsePercent:
    def test_parse_percent_integer(self) -> None:
        assert parse_percent("25%") == 0.25

    def test_parse_percent_without_sign(self) -> None:
        # Accept bare number too; treat it as already a percentage.
        assert parse_percent("25") == 0.25

    def test_parse_percent_decimal(self) -> None:
        assert parse_percent("12.5%") == 0.125

    def test_parse_percent_negative(self) -> None:
        assert parse_percent("-5%") == -0.05

    def test_parse_percent_over_one_hundred(self) -> None:
        assert parse_percent("150%") == 1.5

    def test_parse_percent_zero(self) -> None:
        assert parse_percent("0%") == 0.0

    def test_parse_percent_with_separator(self) -> None:
        assert parse_percent("1,234%") == 12.34

    def test_parse_percent_empty_raises(self) -> None:
        with pytest.raises(NumParseError):
            parse_percent("")

    def test_parse_percent_bad_raises(self) -> None:
        with pytest.raises(NumParseError):
            parse_percent("not%")

    def test_parse_percent_default(self) -> None:
        assert parse_percent("bad", default=0.0) == 0.0

    def test_parse_percent_rejects_non_string(self) -> None:
        with pytest.raises(TypeError):
            parse_percent(0.25)  # type: ignore[arg-type]

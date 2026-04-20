"""Tests for :func:`numparse.parse`, :func:`parse_int`, :func:`parse_float`."""

from __future__ import annotations

import math

import pytest

from numparse import NumParseError, parse, parse_float, parse_int


class TestParseSimpleIntegers:
    def test_parse_zero(self) -> None:
        assert parse("0") == 0

    def test_parse_positive_int(self) -> None:
        assert parse("42") == 42

    def test_parse_negative_int(self) -> None:
        assert parse("-7") == -7

    def test_parse_plus_sign(self) -> None:
        assert parse("+99") == 99

    def test_parse_unicode_minus(self) -> None:
        # U+2212 MINUS SIGN should be treated as a minus.
        assert parse("\u22123") == -3

    def test_parse_leading_trailing_whitespace(self) -> None:
        assert parse("   42   ") == 42

    def test_parse_returns_int_for_whole_value(self) -> None:
        result = parse("1000")
        assert isinstance(result, int)
        assert result == 1000


class TestParseFloats:
    def test_parse_simple_float(self) -> None:
        assert parse("3.14") == pytest.approx(3.14)

    def test_parse_negative_float(self) -> None:
        assert parse("-0.5") == -0.5

    def test_parse_scientific_notation(self) -> None:
        assert parse("1.5e3") == 1500.0

    def test_parse_scientific_uppercase_e(self) -> None:
        assert parse("2.5E-3") == pytest.approx(0.0025)

    def test_parse_leading_dot(self) -> None:
        assert parse(".5") == 0.5

    def test_parse_trailing_dot(self) -> None:
        assert parse("5.") == 5.0

    def test_parse_returns_float_for_decimal(self) -> None:
        assert isinstance(parse("1.5"), float)


class TestParseThousandSeparators:
    def test_parse_comma_separator(self) -> None:
        assert parse("1,000") == 1000

    def test_parse_multiple_commas(self) -> None:
        assert parse("1,234,567") == 1_234_567

    def test_parse_comma_with_decimal(self) -> None:
        assert parse("1,234.56") == pytest.approx(1234.56)

    def test_parse_space_separator(self) -> None:
        assert parse("1 234 567") == 1_234_567

    def test_parse_underscore_separator(self) -> None:
        assert parse("1_000_000") == 1_000_000

    def test_parse_mixed_separators_reject(self) -> None:
        # We accept ONE type of separator at a time; mixing is malformed.
        with pytest.raises(NumParseError):
            parse("1,000 000")

    def test_parse_misplaced_comma_rejected(self) -> None:
        # 1,0,0,0 is not a valid grouping.
        with pytest.raises(NumParseError):
            parse("1,0,0,0")

    def test_parse_empty_digit_group_rejected(self) -> None:
        # Two commas in a row produce an empty group between them.
        with pytest.raises(NumParseError):
            parse("1,,000")


class TestParseMagnitudeSuffix:
    def test_parse_k_suffix(self) -> None:
        assert parse("1k") == 1000

    def test_parse_capital_k_suffix(self) -> None:
        assert parse("1K") == 1000

    def test_parse_fractional_k(self) -> None:
        assert parse("1.5k") == 1500

    def test_parse_m_suffix(self) -> None:
        assert parse("2M") == 2_000_000

    def test_parse_b_suffix_is_billion(self) -> None:
        assert parse("3B") == 3_000_000_000

    def test_parse_g_suffix_is_billion(self) -> None:
        assert parse("4G") == 4_000_000_000

    def test_parse_t_suffix_is_trillion(self) -> None:
        assert parse("1T") == 1_000_000_000_000

    def test_parse_suffix_with_space(self) -> None:
        assert parse("2.5 M") == 2_500_000

    def test_parse_suffix_returns_int_when_whole(self) -> None:
        assert isinstance(parse("2k"), int)

    def test_parse_suffix_returns_float_when_fractional(self) -> None:
        # 1.2345k = 1234.5 — not a whole number.
        assert isinstance(parse("1.2345k"), float)

    def test_parse_bare_suffix_rejected(self) -> None:
        with pytest.raises(NumParseError):
            parse("k")

    def test_parse_unknown_suffix_rejected(self) -> None:
        with pytest.raises(NumParseError):
            parse("1Z")


class TestParseCurrency:
    def test_parse_dollar_prefix(self) -> None:
        assert parse("$1,234.56") == pytest.approx(1234.56)

    def test_parse_euro_prefix(self) -> None:
        assert parse("€1000") == 1000

    def test_parse_euro_suffix(self) -> None:
        assert parse("1234€") == 1234

    def test_parse_pound_prefix(self) -> None:
        assert parse("£99.99") == pytest.approx(99.99)

    def test_parse_rupee_prefix(self) -> None:
        assert parse("₹500") == 500

    def test_parse_yen_prefix(self) -> None:
        assert parse("¥10000") == 10000

    def test_parse_currency_with_suffix(self) -> None:
        assert parse("$1.5M") == 1_500_000


class TestParseErrorsAndDefault:
    def test_parse_empty_raises(self) -> None:
        with pytest.raises(NumParseError):
            parse("")

    def test_parse_whitespace_only_raises(self) -> None:
        with pytest.raises(NumParseError):
            parse("   ")

    def test_parse_garbage_raises(self) -> None:
        with pytest.raises(NumParseError):
            parse("not a number")

    def test_parse_default_on_failure(self) -> None:
        assert parse("bad", default=0) == 0

    def test_parse_default_none(self) -> None:
        assert parse("bad", default=None) is None

    def test_parse_default_not_used_on_success(self) -> None:
        assert parse("42", default=999) == 42

    def test_parse_rejects_non_string(self) -> None:
        with pytest.raises(TypeError):
            parse(42)  # type: ignore[arg-type]

    def test_parse_rejects_none(self) -> None:
        with pytest.raises(TypeError):
            parse(None)  # type: ignore[arg-type]


class TestParseInt:
    def test_parse_int_whole(self) -> None:
        assert parse_int("42") == 42

    def test_parse_int_with_separator(self) -> None:
        assert parse_int("1,234") == 1234

    def test_parse_int_rejects_decimal(self) -> None:
        with pytest.raises(NumParseError):
            parse_int("3.14")

    def test_parse_int_accepts_fractional_suffix_that_resolves_to_int(self) -> None:
        assert parse_int("1.5k") == 1500

    def test_parse_int_rejects_fractional_suffix_that_does_not_resolve(self) -> None:
        with pytest.raises(NumParseError):
            parse_int("1.5k1")  # trailing garbage

    def test_parse_int_rejects_non_integer_magnitude(self) -> None:
        with pytest.raises(NumParseError):
            parse_int("1.2345k")  # = 1234.5, not integer

    def test_parse_int_default(self) -> None:
        assert parse_int("oops", default=-1) == -1

    def test_parse_int_negative(self) -> None:
        assert parse_int("-1000") == -1000

    def test_parse_int_accepts_whole_float(self) -> None:
        # "3.0" parses to float(3.0); parse_int collapses it back to int.
        result = parse_int("3.0")
        assert result == 3
        assert isinstance(result, int)


class TestParseFloat:
    def test_parse_float_basic(self) -> None:
        assert parse_float("3.14") == 3.14

    def test_parse_float_int_input(self) -> None:
        result = parse_float("5")
        assert isinstance(result, float)
        assert result == 5.0

    def test_parse_float_inf(self) -> None:
        assert math.isinf(parse_float("inf"))

    def test_parse_float_negative_inf(self) -> None:
        assert parse_float("-inf") == -math.inf

    def test_parse_float_nan(self) -> None:
        assert math.isnan(parse_float("nan"))

    def test_parse_float_default(self) -> None:
        assert parse_float("", default=0.0) == 0.0

    def test_parse_float_rejects_inf_for_plain_parse(self) -> None:
        # `parse` is for ordinary numbers — inf/nan require parse_float.
        with pytest.raises(NumParseError):
            parse("inf")

    def test_parse_float_rejects_nan_for_plain_parse(self) -> None:
        with pytest.raises(NumParseError):
            parse("nan")

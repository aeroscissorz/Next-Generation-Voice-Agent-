"""
Unit tests for extract_user_id_from_spoken() in helpers.py
Covers requirements 2.1, 2.2, 4.1, 4.2
"""

import logging
import pytest
from utils.helpers import (
    extract_user_id_from_spoken,
    USER_ID_MIN_LENGTH,
    USER_ID_MAX_LENGTH,
)


class TestExtractUserIdFromSpoken:
    """Tests for digit-only extraction and length validation."""

    # --- Requirement 2.1: digits only ---

    def test_strips_letters_keeps_digits(self):
        assert extract_user_id_from_spoken("abc123def45") == "12345"

    def test_strips_spaces_and_dashes(self):
        assert extract_user_id_from_spoken("1 0 1") == "101"

    def test_strips_special_characters(self):
        assert extract_user_id_from_spoken("12-34-56") == "123456"

    def test_mixed_alphanumeric_returns_digits_only(self):
        assert extract_user_id_from_spoken("user42id") == "42"

    # --- Requirement 2.2: length bounds ---

    def test_single_digit_returns_empty(self):
        assert extract_user_id_from_spoken("5") == ""

    def test_two_digits_is_valid(self):
        assert extract_user_id_from_spoken("42") == "42"

    def test_ten_digits_is_valid(self):
        assert extract_user_id_from_spoken("1234567890") == "1234567890"

    def test_eleven_digits_returns_empty(self):
        assert extract_user_id_from_spoken("12345678901") == ""

    def test_empty_string_returns_empty(self):
        assert extract_user_id_from_spoken("") == ""

    def test_whitespace_only_returns_empty(self):
        assert extract_user_id_from_spoken("   ") == ""

    def test_no_digits_returns_empty(self):
        assert extract_user_id_from_spoken("hello world") == ""

    # --- Requirements 4.1, 4.2: logging ---

    def test_logs_raw_and_normalized(self, caplog):
        with caplog.at_level(logging.INFO, logger="helpers"):
            extract_user_id_from_spoken("abc123")
        assert "raw input='abc123'" in caplog.text
        assert "normalized output='123'" in caplog.text

    def test_logs_rejection_reason_for_too_short(self, caplog):
        with caplog.at_level(logging.INFO, logger="helpers"):
            extract_user_id_from_spoken("5")
        assert "rejected" in caplog.text
        assert "digit count 1" in caplog.text

    def test_logs_rejection_reason_for_too_long(self, caplog):
        with caplog.at_level(logging.INFO, logger="helpers"):
            extract_user_id_from_spoken("12345678901")
        assert "rejected" in caplog.text
        assert "digit count 11" in caplog.text

    def test_no_rejection_log_for_valid_input(self, caplog):
        with caplog.at_level(logging.INFO, logger="helpers"):
            extract_user_id_from_spoken("42")
        assert "rejected" not in caplog.text


class TestConstants:
    """Verify the validation constants are set correctly."""

    def test_min_length(self):
        assert USER_ID_MIN_LENGTH == 2

    def test_max_length(self):
        assert USER_ID_MAX_LENGTH == 10

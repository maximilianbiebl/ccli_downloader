"""Tests for the cookie-based login functionality."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure imports work from the project root
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from get_cookies_and_token import get_cookie_and_token, validate_cookies
from update_cookies import (
    are_cookies_captured,
    extract_required_cookies,
    ESSENTIAL_COOKIES,
    OPTIONAL_COOKIES,
    ALL_KNOWN_COOKIES,
    ANTIFORGERY_COOKIE_PREFIX,
    CLOUDFLARE_COOKIES,
)
from browser_utils import detect_chrome_version
from settings import load_settings, save_settings, DEFAULT_SETTINGS
from lyrics_processing import process_lyrics_file


class TestValidateCookies(unittest.TestCase):
    """Tests for cookie validation logic."""

    def test_valid_cookie_string(self):
        cookie = "CCLI_JWT_AUTH=abc123; ARRAffinity=xyz; CCLI_AUTH=def"
        self.assertTrue(validate_cookies(cookie))

    def test_valid_cookie_string_with_cf_clearance(self):
        cookie = "CCLI_JWT_AUTH=abc123; ARRAffinity=xyz; cf_clearance=abc"
        self.assertTrue(validate_cookies(cookie))

    def test_missing_jwt_auth(self):
        cookie = "ARRAffinity=xyz; CCLI_AUTH=def"
        self.assertFalse(validate_cookies(cookie))

    def test_missing_arr_affinity(self):
        cookie = "CCLI_JWT_AUTH=abc123; CCLI_AUTH=def"
        self.assertFalse(validate_cookies(cookie))

    def test_empty_string(self):
        self.assertFalse(validate_cookies(""))

    def test_warns_without_cf_clearance(self):
        """validate_cookies still returns True without cf_clearance but prints warning."""
        cookie = "CCLI_JWT_AUTH=abc123; ARRAffinity=xyz; CCLI_AUTH=def"
        self.assertTrue(validate_cookies(cookie))


class TestGetCookieAndToken(unittest.TestCase):
    """Tests for loading cookies and token from files."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.orig_dir)

    def test_missing_cookie_file(self):
        """Returns None when Cookie.txt doesn't exist."""
        token, cookie = get_cookie_and_token()
        self.assertIsNone(token)
        self.assertIsNone(cookie)

    def test_missing_token_file(self):
        """Returns None when RequestVerificationToken.txt doesn't exist."""
        with open("Cookie.txt", "w") as f:
            f.write("CCLI_JWT_AUTH=abc; ARRAffinity=xyz")
        token, cookie = get_cookie_and_token()
        self.assertIsNone(token)
        self.assertIsNone(cookie)

    def test_empty_cookie_file(self):
        """Returns None when Cookie.txt is empty."""
        with open("Cookie.txt", "w") as f:
            f.write("")
        with open("RequestVerificationToken.txt", "w") as f:
            f.write("test_token")
        token, cookie = get_cookie_and_token()
        self.assertIsNone(token)
        self.assertIsNone(cookie)

    def test_invalid_cookies(self):
        """Returns None when Cookie.txt has invalid/incomplete cookies."""
        with open("Cookie.txt", "w") as f:
            f.write("some_random_cookie=value")
        with open("RequestVerificationToken.txt", "w") as f:
            f.write("test_token")
        token, cookie = get_cookie_and_token()
        self.assertIsNone(token)
        self.assertIsNone(cookie)

    def test_valid_files(self):
        """Returns token and cookie when files are valid."""
        cookie_str = "CCLI_JWT_AUTH=jwt_value; ARRAffinity=arr_value; CCLI_AUTH=auth_value"
        with open("Cookie.txt", "w") as f:
            f.write(cookie_str)
        with open("RequestVerificationToken.txt", "w") as f:
            f.write("my_token")
        token, cookie = get_cookie_and_token()
        self.assertEqual(token, "my_token")
        self.assertEqual(cookie, cookie_str)

    def test_valid_files_with_cf_clearance(self):
        """Returns token and cookie when files include cf_clearance."""
        cookie_str = "CCLI_JWT_AUTH=jwt_value; ARRAffinity=arr_value; cf_clearance=cf_val"
        with open("Cookie.txt", "w") as f:
            f.write(cookie_str)
        with open("RequestVerificationToken.txt", "w") as f:
            f.write("my_token")
        token, cookie = get_cookie_and_token()
        self.assertEqual(token, "my_token")
        self.assertEqual(cookie, cookie_str)


class TestAreCookiesCaptured(unittest.TestCase):
    """Tests for the are_cookies_captured function."""

    def test_all_cookies_present(self):
        cookies = [
            {"name": "ARRAffinity", "value": "1"},
            {"name": "ARRAffinitySameSite", "value": "2"},
            {"name": "CCLI_AUTH", "value": "3"},
            {"name": "CCLI_JWT_AUTH", "value": "4"},
            {"name": ".AspNetCore.Session", "value": "5"},
            {"name": ".AspNetCore.Antiforgery.abc", "value": "6"},
        ]
        self.assertTrue(are_cookies_captured(cookies))

    def test_essential_cookies_only(self):
        """Succeeds when only essential cookies are present."""
        cookies = [
            {"name": "CCLI_JWT_AUTH", "value": "4"},
            {"name": "ARRAffinity", "value": "1"},
        ]
        self.assertTrue(are_cookies_captured(cookies))

    def test_missing_essential_cookie(self):
        """Fails when an essential cookie is missing."""
        cookies = [
            {"name": "ARRAffinity", "value": "1"},
            {"name": "CCLI_AUTH", "value": "3"},
            {"name": ".AspNetCore.Antiforgery.abc", "value": "6"},
        ]
        self.assertFalse(are_cookies_captured(cookies))

    def test_missing_arr_affinity(self):
        """Fails when ARRAffinity is missing."""
        cookies = [
            {"name": "CCLI_JWT_AUTH", "value": "4"},
            {"name": "CCLI_AUTH", "value": "3"},
        ]
        self.assertFalse(are_cookies_captured(cookies))

    def test_optional_cookies_not_required(self):
        """Succeeds without optional cookies like .AspNetCore.Session."""
        cookies = [
            {"name": "CCLI_JWT_AUTH", "value": "4"},
            {"name": "ARRAffinity", "value": "1"},
        ]
        self.assertTrue(are_cookies_captured(cookies))

    def test_antiforgery_not_required(self):
        """Succeeds without antiforgery cookies."""
        cookies = [
            {"name": "CCLI_JWT_AUTH", "value": "4"},
            {"name": "ARRAffinity", "value": "1"},
        ]
        self.assertTrue(are_cookies_captured(cookies))

    def test_empty_cookies(self):
        self.assertFalse(are_cookies_captured([]))


class TestExtractRequiredCookies(unittest.TestCase):
    """Tests for extract_required_cookies function."""

    def test_filters_known_cookies(self):
        cookies = [
            {"name": "ARRAffinity", "value": "1"},
            {"name": "random_cookie", "value": "ignored"},
            {"name": "CCLI_JWT_AUTH", "value": "4"},
            {"name": ".AspNetCore.Antiforgery.abc", "value": "6"},
        ]
        result = extract_required_cookies(cookies)
        self.assertEqual(result["ARRAffinity"], "1")
        self.assertEqual(result["CCLI_JWT_AUTH"], "4")
        self.assertEqual(result[".AspNetCore.Antiforgery.abc"], "6")
        self.assertNotIn("random_cookie", result)

    def test_captures_optional_cookies(self):
        """Optional cookies like CCLI_AUTH are captured when present."""
        cookies = [
            {"name": "ARRAffinity", "value": "1"},
            {"name": "CCLI_JWT_AUTH", "value": "4"},
            {"name": "CCLI_AUTH", "value": "3"},
            {"name": ".AspNetCore.Session", "value": "5"},
        ]
        result = extract_required_cookies(cookies)
        self.assertEqual(result["CCLI_AUTH"], "3")
        self.assertEqual(result[".AspNetCore.Session"], "5")

    def test_captures_cf_clearance(self):
        """cf_clearance cookie should be captured when present."""
        cookies = [
            {"name": "ARRAffinity", "value": "1"},
            {"name": "cf_clearance", "value": "cloudflare_token"},
            {"name": "random_cookie", "value": "ignored"},
        ]
        result = extract_required_cookies(cookies)
        self.assertEqual(result["cf_clearance"], "cloudflare_token")
        self.assertEqual(result["ARRAffinity"], "1")
        self.assertNotIn("random_cookie", result)

    def test_works_without_cf_clearance(self):
        """extract_required_cookies works when cf_clearance is not present."""
        cookies = [
            {"name": "ARRAffinity", "value": "1"},
            {"name": "CCLI_JWT_AUTH", "value": "4"},
        ]
        result = extract_required_cookies(cookies)
        self.assertEqual(result["ARRAffinity"], "1")
        self.assertEqual(result["CCLI_JWT_AUTH"], "4")
        self.assertNotIn("cf_clearance", result)

    def test_empty_input(self):
        result = extract_required_cookies([])
        self.assertEqual(result, {})


class TestCloudflareConstants(unittest.TestCase):
    """Tests for Cloudflare-related constants."""

    def test_cloudflare_cookies_defined(self):
        self.assertIn("cf_clearance", CLOUDFLARE_COOKIES)


class TestDetectChromeVersion(unittest.TestCase):
    """Tests for Chrome version detection."""

    @patch("browser_utils.subprocess.check_output")
    def test_detects_version_from_output(self, mock_check):
        """Parses major version from chrome --version output."""
        mock_check.return_value = "Google Chrome 145.0.7632.160\n"
        version = detect_chrome_version()
        self.assertEqual(version, 145)

    @patch("browser_utils.subprocess.check_output")
    def test_detects_chromium_version(self, mock_check):
        """Parses major version from Chromium output."""
        mock_check.return_value = "Chromium 120.0.6099.71\n"
        version = detect_chrome_version()
        self.assertEqual(version, 120)

    @patch("browser_utils.subprocess.check_output", side_effect=FileNotFoundError)
    def test_returns_none_when_chrome_not_found(self, mock_check):
        """Returns None when no Chrome binary is found."""
        version = detect_chrome_version()
        self.assertIsNone(version)

    @patch("browser_utils.subprocess.check_output")
    def test_handles_unexpected_output(self, mock_check):
        """Returns None when output doesn't match version pattern."""
        mock_check.return_value = "some unexpected output"
        version = detect_chrome_version()
        self.assertIsNone(version)

    @patch("browser_utils.subprocess.check_output")
    def test_windows_registry_output(self, mock_check):
        """Parses version from Windows registry query output."""
        mock_check.return_value = (
            "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon\n"
            "    version    REG_SZ    146.0.7890.100\n"
        )
        version = detect_chrome_version()
        self.assertEqual(version, 146)


class TestSettings(unittest.TestCase):
    """Tests for settings persistence."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.orig_dir)

    def test_load_defaults_when_no_file(self):
        """Returns defaults when settings.json doesn't exist."""
        settings = load_settings()
        self.assertEqual(settings["output_folder"], "./songs")
        self.assertEqual(settings["line_separator"], "//")
        self.assertEqual(settings["lines_per_slide"], 2)

    def test_save_and_load(self):
        """Round-trips settings through save and load."""
        settings = {
            "output_folder": "/tmp/mydir",
            "line_separator": "---",
            "lines_per_slide": 4,
        }
        save_settings(settings)
        loaded = load_settings()
        self.assertEqual(loaded["output_folder"], "/tmp/mydir")
        self.assertEqual(loaded["line_separator"], "---")
        self.assertEqual(loaded["lines_per_slide"], 4)

    def test_load_merges_with_defaults(self):
        """Partial settings file gets merged with defaults."""
        with open("settings.json", "w") as f:
            json.dump({"output_folder": "/custom"}, f)
        loaded = load_settings()
        self.assertEqual(loaded["output_folder"], "/custom")
        self.assertEqual(loaded["line_separator"], "//")
        self.assertEqual(loaded["lines_per_slide"], 2)

    def test_load_handles_corrupted_file(self):
        """Returns defaults when settings.json is invalid JSON."""
        with open("settings.json", "w") as f:
            f.write("not valid json")
        settings = load_settings()
        self.assertEqual(settings, DEFAULT_SETTINGS)


class TestProcessLyrics(unittest.TestCase):
    """Tests for lyrics post-processing with line separators."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def test_adds_separator_every_2_lines(self):
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4")

        process_lyrics_file(filepath, "//", 2)

        with open(filepath, "r") as f:
            lines = f.read().split("\n")

        self.assertEqual(lines[0], "Line 1")
        self.assertEqual(lines[1], "Line 2")
        self.assertEqual(lines[2], "//")
        self.assertEqual(lines[3], "Line 3")
        self.assertEqual(lines[4], "Line 4")
        self.assertEqual(lines[5], "//")

    def test_custom_separator(self):
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("A\nB\nC\nD")

        process_lyrics_file(filepath, "---", 2)

        with open(filepath, "r") as f:
            content = f.read()
        self.assertIn("---", content)
        self.assertNotIn("//", content)

    def test_lines_per_slide_3(self):
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("A\nB\nC\nD\nE\nF")

        process_lyrics_file(filepath, "//", 3)

        with open(filepath, "r") as f:
            lines = f.read().split("\n")

        # After A, B, C → //, then D, E, F → //
        self.assertEqual(lines[3], "//")
        self.assertEqual(lines[7], "//")

    def test_skips_empty_lines_in_count(self):
        """Empty lines are preserved but not counted."""
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("A\nB\n\nC\nD")

        process_lyrics_file(filepath, "//", 2)

        with open(filepath, "r") as f:
            lines = f.read().split("\n")

        # A, B counted → // after B, then empty line, then C, D → //
        self.assertEqual(lines[0], "A")
        self.assertEqual(lines[1], "B")
        self.assertEqual(lines[2], "//")
        self.assertEqual(lines[3], "")
        self.assertEqual(lines[4], "C")
        self.assertEqual(lines[5], "D")
        self.assertEqual(lines[6], "//")

    def test_no_processing_when_separator_empty(self):
        """No separator added when separator string is empty."""
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("A\nB\nC\nD")

        process_lyrics_file(filepath, "", 2)

        with open(filepath, "r") as f:
            content = f.read()
        self.assertEqual(content, "A\nB\nC\nD")

    def test_no_processing_when_lines_per_slide_zero(self):
        """No separator added when lines_per_slide < 1."""
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("A\nB")

        process_lyrics_file(filepath, "//", 0)

        with open(filepath, "r") as f:
            content = f.read()
        self.assertEqual(content, "A\nB")


if __name__ == "__main__":
    unittest.main()

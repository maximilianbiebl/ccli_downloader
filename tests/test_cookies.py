"""Tests for the cookie-based login functionality."""

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
    REQUIRED_COOKIES,
    ANTIFORGERY_COOKIE_PREFIX,
    CLOUDFLARE_COOKIES,
)
from browser_utils import detect_chrome_version


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

    def test_missing_required_cookie(self):
        cookies = [
            {"name": "ARRAffinity", "value": "1"},
            {"name": "CCLI_AUTH", "value": "3"},
            {"name": ".AspNetCore.Antiforgery.abc", "value": "6"},
        ]
        self.assertFalse(are_cookies_captured(cookies))

    def test_missing_antiforgery(self):
        cookies = [
            {"name": "ARRAffinity", "value": "1"},
            {"name": "ARRAffinitySameSite", "value": "2"},
            {"name": "CCLI_AUTH", "value": "3"},
            {"name": "CCLI_JWT_AUTH", "value": "4"},
            {"name": ".AspNetCore.Session", "value": "5"},
        ]
        self.assertFalse(are_cookies_captured(cookies))

    def test_empty_cookies(self):
        self.assertFalse(are_cookies_captured([]))


class TestExtractRequiredCookies(unittest.TestCase):
    """Tests for extract_required_cookies function."""

    def test_filters_required_cookies(self):
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


if __name__ == "__main__":
    unittest.main()

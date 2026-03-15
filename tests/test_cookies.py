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
from lyrics_processing import process_lyrics_file, rename_with_line_count, is_section_label, is_metadata_line, merge_section_labels, merge_section_labels_file


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
        self.assertFalse(settings["use_empty_line_separator"])
        self.assertFalse(settings["add_line_count_to_filename"])

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
        self.assertFalse(loaded["use_empty_line_separator"])
        self.assertFalse(loaded["add_line_count_to_filename"])

    def test_save_and_load_new_settings(self):
        """Round-trips the new boolean settings."""
        settings = {
            "output_folder": "/tmp/test",
            "line_separator": "//",
            "lines_per_slide": 3,
            "use_empty_line_separator": True,
            "add_line_count_to_filename": True,
        }
        save_settings(settings)
        loaded = load_settings()
        self.assertTrue(loaded["use_empty_line_separator"])
        self.assertTrue(loaded["add_line_count_to_filename"])
        self.assertEqual(loaded["lines_per_slide"], 3)

    def test_load_handles_corrupted_file(self):
        """Returns defaults when settings.json is invalid JSON."""
        with open("settings.json", "w") as f:
            f.write("not valid json")
        settings = load_settings()
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_include_metadata_default(self):
        """include_metadata defaults to False."""
        settings = load_settings()
        self.assertFalse(settings["include_metadata"])

    def test_save_and_load_include_metadata(self):
        """Round-trips include_metadata through save and load."""
        settings = dict(DEFAULT_SETTINGS)
        settings["include_metadata"] = True
        save_settings(settings)
        loaded = load_settings()
        self.assertTrue(loaded["include_metadata"])


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

    def test_no_processing_when_separator_none(self):
        """No separator added when separator is None."""
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("A\nB\nC\nD")

        process_lyrics_file(filepath, None, 2)

        with open(filepath, "r") as f:
            content = f.read()
        self.assertEqual(content, "A\nB\nC\nD")

    def test_empty_string_separator_inserts_blank_lines(self):
        """Empty string separator inserts blank lines between slides."""
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4")

        process_lyrics_file(filepath, "", 2)

        with open(filepath, "r") as f:
            lines = f.read().split("\n")

        self.assertEqual(lines[0], "Line 1")
        self.assertEqual(lines[1], "Line 2")
        self.assertEqual(lines[2], "")
        self.assertEqual(lines[3], "Line 3")
        self.assertEqual(lines[4], "Line 4")
        self.assertEqual(lines[5], "")

    def test_no_processing_when_lines_per_slide_zero(self):
        """No separator added when lines_per_slide < 1."""
        filepath = os.path.join(self.test_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("A\nB")

        process_lyrics_file(filepath, "//", 0)

        with open(filepath, "r") as f:
            content = f.read()
        self.assertEqual(content, "A\nB")


class TestRenameWithLineCount(unittest.TestCase):
    """Tests for lyrics_processing.rename_with_line_count."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def test_renames_file_with_line_count(self):
        """Renames 'Song.txt' to 'Song_2-zeilig.txt'."""
        filepath = os.path.join(self.test_dir, "Way Maker.txt")
        with open(filepath, "w") as f:
            f.write("content")

        new_path = rename_with_line_count(filepath, 2)

        self.assertTrue(new_path.endswith("Way Maker_2-zeilig.txt"))
        self.assertTrue(os.path.exists(new_path))
        self.assertFalse(os.path.exists(filepath))

    def test_renames_with_different_line_count(self):
        """Renames with correct line count value."""
        filepath = os.path.join(self.test_dir, "Title.txt")
        with open(filepath, "w") as f:
            f.write("content")

        new_path = rename_with_line_count(filepath, 4)

        self.assertTrue(new_path.endswith("Title_4-zeilig.txt"))
        self.assertTrue(os.path.exists(new_path))

    def test_preserves_file_content(self):
        """File content is preserved after renaming."""
        filepath = os.path.join(self.test_dir, "Test.txt")
        with open(filepath, "w") as f:
            f.write("hello\nworld")

        new_path = rename_with_line_count(filepath, 3)

        with open(new_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "hello\nworld")


class TestIsSectionLabel(unittest.TestCase):
    """Tests for lyrics_processing.is_section_label."""

    def test_verse(self):
        self.assertTrue(is_section_label("Verse 1"))

    def test_chorus(self):
        self.assertTrue(is_section_label("Chorus"))

    def test_bridge(self):
        self.assertTrue(is_section_label("Bridge"))

    def test_pre_chorus_with_number(self):
        self.assertTrue(is_section_label("Pre-Chorus 2"))

    def test_case_insensitive(self):
        self.assertTrue(is_section_label("verse 1"))
        self.assertTrue(is_section_label("CHORUS"))

    def test_tag(self):
        self.assertTrue(is_section_label("Tag"))

    def test_ending(self):
        self.assertTrue(is_section_label("Ending"))

    def test_intro(self):
        self.assertTrue(is_section_label("Intro"))

    def test_interlude(self):
        self.assertTrue(is_section_label("Interlude"))

    def test_outro(self):
        self.assertTrue(is_section_label("Outro"))

    def test_misc(self):
        self.assertTrue(is_section_label("Misc 1"))

    def test_regular_lyrics_not_label(self):
        self.assertFalse(is_section_label("I lay my life down"))

    def test_empty_string_not_label(self):
        self.assertFalse(is_section_label(""))

    def test_already_bracketed_not_label(self):
        self.assertFalse(is_section_label("[Verse 1]"))

    def test_whitespace_stripped(self):
        self.assertTrue(is_section_label("  Verse 1  "))


class TestIsMetadataLine(unittest.TestCase):
    """Tests for lyrics_processing.is_metadata_line."""

    def test_copyright_symbol(self):
        self.assertTrue(is_metadata_line("© 2015 Music by Elevation Worship"))

    def test_ccli_liednummer(self):
        self.assertTrue(is_metadata_line("CCLI-Liednummer: 7051511"))

    def test_ccli_song_number(self):
        self.assertTrue(is_metadata_line("CCLI Song #: 7051511"))

    def test_songselect(self):
        self.assertTrue(is_metadata_line(
            "For use solely with the SongSelect® Terms of Use. All rights reserved. www.ccli.com"
        ))

    def test_ccli_com(self):
        self.assertTrue(is_metadata_line("www.ccli.com"))

    def test_all_rights_reserved(self):
        self.assertTrue(is_metadata_line("All rights reserved."))

    def test_regular_lyrics_not_metadata(self):
        self.assertFalse(is_metadata_line("Are you hurting and broken within"))

    def test_section_label_not_metadata(self):
        self.assertFalse(is_metadata_line("Verse 1"))

    def test_empty_string_not_metadata(self):
        self.assertFalse(is_metadata_line(""))


class TestMergeSectionLabels(unittest.TestCase):
    """Tests for lyrics_processing.merge_section_labels."""

    def test_basic_merge(self):
        text = "Verse 1\nI lay my life down"
        result = merge_section_labels(text)
        self.assertEqual(result, "[Verse 1] I lay my life down")

    def test_multiple_sections(self):
        text = "Verse 1\nLine A\nLine B\nChorus\nLine C"
        result = merge_section_labels(text)
        lines = result.splitlines()
        self.assertEqual(lines[0], "[Verse 1] Line A")
        self.assertEqual(lines[1], "Line B")
        self.assertEqual(lines[2], "[Chorus] Line C")

    def test_empty_lines_between_label_and_content(self):
        text = "Verse 1\n\nI lay my life down"
        result = merge_section_labels(text)
        self.assertEqual(result, "[Verse 1] I lay my life down")

    def test_label_at_end_of_file(self):
        text = "Verse 1\nLine A\nVerse 2"
        result = merge_section_labels(text)
        lines = result.splitlines()
        self.assertEqual(lines[0], "[Verse 1] Line A")
        self.assertEqual(lines[1], "[Verse 2]")

    def test_no_labels(self):
        text = "Line A\nLine B\nLine C"
        result = merge_section_labels(text)
        self.assertEqual(result, text)

    def test_full_song_format(self):
        """Full example matching the problem statement format.

        merge_section_labels strips blank lines so that process_lyrics_file
        can place separators at the correct positions.
        """
        text = (
            "Verse 1\n"
            "I lay my life down at Your feet\n"
            "You're the only One I need\n"
            "\n"
            "Chorus\n"
            "One way Jesus\n"
            "You're the only One that I could live for\n"
            "\n"
            "Verse 2\n"
            "You are always\n"
            "Always there"
        )
        result = merge_section_labels(text)
        lines = result.splitlines()
        self.assertEqual(lines[0], "[Verse 1] I lay my life down at Your feet")
        self.assertEqual(lines[1], "You're the only One I need")
        self.assertEqual(lines[2], "[Chorus] One way Jesus")
        self.assertEqual(lines[3], "You're the only One that I could live for")
        self.assertEqual(lines[4], "[Verse 2] You are always")
        self.assertEqual(lines[5], "Always there")
        self.assertEqual(len(lines), 6)

    def test_strips_title_before_first_section(self):
        """Title line before the first section label should be removed."""
        text = "O Come To The Altar\n\nVerse 1\nI lay my life down"
        result = merge_section_labels(text)
        self.assertEqual(result, "[Verse 1] I lay my life down")

    def test_strips_metadata_footer(self):
        """Footer metadata (author, ©, CCLI number) should be removed."""
        text = (
            "Verse 1\nLine A\nLine B\n\n"
            "Author Name\n"
            "© 2015 Publisher\n"
            "For use solely with the SongSelect® Terms of Use.\n"
            "CCLI-Liednummer: 7051511"
        )
        result = merge_section_labels(text)
        lines = result.splitlines()
        self.assertEqual(lines[0], "[Verse 1] Line A")
        self.assertEqual(lines[1], "Line B")
        self.assertEqual(len(lines), 2)

    def test_strips_title_and_metadata(self):
        """Both title and footer metadata should be stripped together."""
        text = (
            "O Come To The Altar\n\n"
            "Verse 1\n"
            "Are you hurting and broken within\n"
            "Overwhelmed by the weight of your sin\n"
            "Jesus is calling\n\n"
            "Chorus\n"
            "O come to the altar\n"
            "The Father's arms are open wide\n\n"
            "Chris Brown, Mack Brock, Steven Furtick, Wade Joye\n"
            "© 2015 Music by Elevation Worship Publishing\n"
            "For use solely with the SongSelect® Terms of Use. "
            "All rights reserved. www.ccli.com\n"
            "CCLI-Liednummer: 7051511"
        )
        result = merge_section_labels(text)
        lines = result.splitlines()
        self.assertEqual(lines[0], "[Verse 1] Are you hurting and broken within")
        self.assertEqual(lines[1], "Overwhelmed by the weight of your sin")
        self.assertEqual(lines[2], "Jesus is calling")
        self.assertEqual(lines[3], "[Chorus] O come to the altar")
        self.assertEqual(lines[4], "The Father's arms are open wide")
        self.assertEqual(len(lines), 5)

    def test_include_metadata_preserves_title_and_footer(self):
        """With include_metadata=True, title and footer are preserved."""
        text = (
            "O Come To The Altar\n\n"
            "Verse 1\n"
            "Are you hurting and broken within\n"
            "Jesus is calling\n\n"
            "Chris Brown, Mack Brock\n"
            "© 2015 Music by Elevation Worship Publishing\n"
            "CCLI-Liednummer: 7051511"
        )
        result = merge_section_labels(text, include_metadata=True)
        lines = result.splitlines()
        self.assertEqual(lines[0], "O Come To The Altar")
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[2], "[Verse 1] Are you hurting and broken within")
        self.assertEqual(lines[3], "Jesus is calling")
        self.assertEqual(lines[4], "")
        self.assertEqual(lines[5], "Chris Brown, Mack Brock")
        self.assertEqual(lines[6], "© 2015 Music by Elevation Worship Publishing")
        self.assertEqual(lines[7], "CCLI-Liednummer: 7051511")
        self.assertEqual(len(lines), 8)

    def test_include_metadata_false_strips_all(self):
        """With include_metadata=False (default), title and footer are stripped."""
        text = (
            "Song Title\n\n"
            "Verse 1\nLine A\n\n"
            "Author Name\n"
            "© 2020 Publisher\n"
            "CCLI-Liednummer: 123456"
        )
        result = merge_section_labels(text, include_metadata=False)
        lines = result.splitlines()
        self.assertEqual(lines[0], "[Verse 1] Line A")
        self.assertEqual(len(lines), 1)

    def test_include_metadata_no_footer(self):
        """With include_metadata=True but no footer, only title is kept."""
        text = "My Song Title\n\nVerse 1\nLine A\nLine B"
        result = merge_section_labels(text, include_metadata=True)
        lines = result.splitlines()
        self.assertEqual(lines[0], "My Song Title")
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[2], "[Verse 1] Line A")
        self.assertEqual(lines[3], "Line B")
        self.assertEqual(len(lines), 4)

    def test_include_metadata_no_title(self):
        """With include_metadata=True but no title, only footer is kept."""
        text = (
            "Verse 1\nLine A\n\n"
            "Author Name\n"
            "© 2020 Publisher"
        )
        result = merge_section_labels(text, include_metadata=True)
        lines = result.splitlines()
        self.assertEqual(lines[0], "[Verse 1] Line A")
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[2], "Author Name")
        self.assertEqual(lines[3], "© 2020 Publisher")
        self.assertEqual(len(lines), 4)


class TestMergeSectionLabelsFile(unittest.TestCase):
    """Tests for lyrics_processing.merge_section_labels_file."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def test_merges_labels_in_file(self):
        filepath = os.path.join(self.test_dir, "song.txt")
        with open(filepath, "w") as f:
            f.write("Verse 1\nI lay my life down\nChorus\nOne way")

        merge_section_labels_file(filepath)

        with open(filepath, "r") as f:
            lines = f.read().splitlines()

        self.assertEqual(lines[0], "[Verse 1] I lay my life down")
        self.assertEqual(lines[1], "[Chorus] One way")

    def test_no_labels_unchanged(self):
        filepath = os.path.join(self.test_dir, "song.txt")
        with open(filepath, "w") as f:
            f.write("Line A\nLine B")

        merge_section_labels_file(filepath)

        with open(filepath, "r") as f:
            content = f.read()
        self.assertEqual(content, "Line A\nLine B")

    def test_strips_blank_lines_from_ccli_format(self):
        """CCLI files have blank lines between sections that should be stripped."""
        filepath = os.path.join(self.test_dir, "song.txt")
        with open(filepath, "w") as f:
            f.write(
                "Verse 1\n"
                "Are you hurting and broken within\n"
                "Overwhelmed by the weight of your sin\n"
                "Jesus is calling\n"
                "\n"
                "Have you come to the end of yourself\n"
                "Do you thirst for a drink from the well\n"
                "\n"
                "Jesus is calling\n"
                "\n"
                "Chorus\n"
                "O come to the altar\n"
                "The Father's arms are open wide\n"
                "Forgiveness was bought with\n"
            )

        merge_section_labels_file(filepath)

        with open(filepath, "r") as f:
            lines = f.read().splitlines()

        # All blank lines should be stripped
        self.assertEqual(lines[0], "[Verse 1] Are you hurting and broken within")
        self.assertEqual(lines[1], "Overwhelmed by the weight of your sin")
        self.assertEqual(lines[2], "Jesus is calling")
        self.assertEqual(lines[3], "Have you come to the end of yourself")
        self.assertEqual(lines[4], "Do you thirst for a drink from the well")
        self.assertEqual(lines[5], "Jesus is calling")
        self.assertEqual(lines[6], "[Chorus] O come to the altar")
        self.assertEqual(lines[7], "The Father's arms are open wide")
        self.assertEqual(lines[8], "Forgiveness was bought with")
        self.assertEqual(len(lines), 9)

    def test_end_to_end_freeshow_format(self):
        """Full pipeline: merge labels then add empty line separators."""
        filepath = os.path.join(self.test_dir, "song.txt")
        with open(filepath, "w") as f:
            f.write(
                "Verse 1\n"
                "Are you hurting and broken within\n"
                "Overwhelmed by the weight of your sin\n"
                "Jesus is calling\n"
                "\n"
                "Have you come to the end of yourself\n"
                "Do you thirst for a drink from the well\n"
                "\n"
                "Jesus is calling\n"
                "\n"
                "Chorus\n"
                "O come to the altar\n"
                "The Father's arms are open wide\n"
                "Forgiveness was bought with\n"
            )

        merge_section_labels_file(filepath)
        process_lyrics_file(filepath, "", 2)

        with open(filepath, "r") as f:
            lines = f.read().splitlines()

        # Expected FreeShow format: 2 content lines, blank, 2 content lines, blank, ...
        self.assertEqual(lines[0], "[Verse 1] Are you hurting and broken within")
        self.assertEqual(lines[1], "Overwhelmed by the weight of your sin")
        self.assertEqual(lines[2], "")
        self.assertEqual(lines[3], "Jesus is calling")
        self.assertEqual(lines[4], "Have you come to the end of yourself")
        self.assertEqual(lines[5], "")
        self.assertEqual(lines[6], "Do you thirst for a drink from the well")
        self.assertEqual(lines[7], "Jesus is calling")
        self.assertEqual(lines[8], "")
        self.assertEqual(lines[9], "[Chorus] O come to the altar")
        self.assertEqual(lines[10], "The Father's arms are open wide")
        self.assertEqual(lines[11], "")
        self.assertEqual(lines[12], "Forgiveness was bought with")

    def test_end_to_end_real_ccli_download(self):
        """Full pipeline with a realistic CCLI download including title and footer."""
        filepath = os.path.join(self.test_dir, "song.txt")
        with open(filepath, "w") as f:
            f.write(
                "O Come To The Altar\n"
                "\n"
                "Verse 1\n"
                "Are you hurting and broken within\n"
                "Overwhelmed by the weight of your sin\n"
                "Jesus is calling\n"
                "\n"
                "Chorus\n"
                "O come to the altar\n"
                "The Father's arms are open wide\n"
                "\n"
                "Chris Brown, Mack Brock, Steven Furtick, Wade Joye\n"
                "© 2015 Music by Elevation Worship Publishing\n"
                "For use solely with the SongSelect® Terms of Use. "
                "All rights reserved. www.ccli.com\n"
                "CCLI-Liednummer: 7051511\n"
            )

        merge_section_labels_file(filepath)
        process_lyrics_file(filepath, "", 2)

        with open(filepath, "r") as f:
            lines = f.read().splitlines()

        # Title and metadata should be stripped; only lyrics remain
        self.assertEqual(lines[0], "[Verse 1] Are you hurting and broken within")
        self.assertEqual(lines[1], "Overwhelmed by the weight of your sin")
        self.assertEqual(lines[2], "")
        self.assertEqual(lines[3], "Jesus is calling")
        self.assertEqual(lines[4], "[Chorus] O come to the altar")
        self.assertEqual(lines[5], "")
        self.assertEqual(lines[6], "The Father's arms are open wide")
        # No author/copyright/CCLI lines should appear
        self.assertEqual(len(lines), 7)

    def test_end_to_end_with_include_metadata(self):
        """Full pipeline with include_metadata=True preserves title and footer."""
        filepath = os.path.join(self.test_dir, "song.txt")
        with open(filepath, "w") as f:
            f.write(
                "O Come To The Altar\n"
                "\n"
                "Verse 1\n"
                "Are you hurting and broken within\n"
                "Jesus is calling\n"
                "\n"
                "Chris Brown, Mack Brock\n"
                "© 2015 Music by Elevation Worship Publishing\n"
                "CCLI-Liednummer: 7051511\n"
            )

        merge_section_labels_file(filepath, include_metadata=True)

        with open(filepath, "r") as f:
            lines = f.read().splitlines()

        # Title at top, lyrics in middle, footer at bottom
        self.assertEqual(lines[0], "O Come To The Altar")
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[2], "[Verse 1] Are you hurting and broken within")
        self.assertEqual(lines[3], "Jesus is calling")
        self.assertEqual(lines[4], "")
        self.assertEqual(lines[5], "Chris Brown, Mack Brock")
        self.assertEqual(lines[6], "© 2015 Music by Elevation Worship Publishing")
        self.assertEqual(lines[7], "CCLI-Liednummer: 7051511")
        self.assertEqual(len(lines), 8)


class TestTryExtractText(unittest.TestCase):
    """Tests for scraping_helpers.try_extract_text."""

    def setUp(self):
        from scraping_helpers import try_extract_text
        self.extract = try_extract_text

    def test_returns_text_from_first_matching_selector(self):
        """Returns text when the first selector matches."""
        mock_el = MagicMock()
        mock_el.text = "Amazing Grace"
        parent = MagicMock()
        parent.find_element.return_value = mock_el

        selectors = [("by_class", "title")]
        result = self.extract(parent, selectors)
        self.assertEqual(result, "Amazing Grace")

    def test_falls_back_to_textContent_when_text_empty(self):
        """Falls back to textContent when .text is empty."""
        mock_el = MagicMock()
        mock_el.text = ""
        mock_el.get_attribute.return_value = "Hidden Title"
        parent = MagicMock()
        parent.find_element.return_value = mock_el

        selectors = [("by_class", "title")]
        result = self.extract(parent, selectors)
        self.assertEqual(result, "Hidden Title")

    def test_tries_next_selector_on_exception(self):
        """Skips selectors that raise exceptions."""
        good_el = MagicMock()
        good_el.text = "Found It"

        parent = MagicMock()
        parent.find_element.side_effect = [Exception("not found"), good_el]

        selectors = [("by_class", "bad"), ("by_class", "good")]
        result = self.extract(parent, selectors)
        self.assertEqual(result, "Found It")

    def test_returns_empty_when_all_fail(self):
        """Returns empty string when no selector works."""
        parent = MagicMock()
        parent.find_element.side_effect = Exception("not found")

        selectors = [("by_class", "title"), ("by_class", "name")]
        result = self.extract(parent, selectors)
        self.assertEqual(result, "")

    def test_skips_empty_text_tries_next(self):
        """Skips selectors that return empty text and textContent."""
        empty_el = MagicMock()
        empty_el.text = ""
        empty_el.get_attribute.return_value = ""

        good_el = MagicMock()
        good_el.text = "Song Title"

        parent = MagicMock()
        parent.find_element.side_effect = [empty_el, good_el]

        selectors = [("by_class", "empty"), ("by_class", "title")]
        result = self.extract(parent, selectors)
        self.assertEqual(result, "Song Title")


class TestTryExtractLink(unittest.TestCase):
    """Tests for scraping_helpers.try_extract_link."""

    def setUp(self):
        from scraping_helpers import try_extract_link
        self.extract_link = try_extract_link

    def test_returns_href_from_element(self):
        """Returns href directly from element."""
        el = MagicMock()
        el.get_attribute.return_value = "https://songselect.ccli.com/Songs/123"
        self.assertEqual(
            self.extract_link(el), "https://songselect.ccli.com/Songs/123"
        )

    def test_falls_back_to_child_a_tag(self):
        """Falls back to child <a> tag when element has no href."""
        child_a = MagicMock()
        child_a.get_attribute.return_value = "https://songselect.ccli.com/Songs/456"

        el = MagicMock()
        el.get_attribute.return_value = None
        el.find_element.return_value = child_a

        self.assertEqual(
            self.extract_link(el), "https://songselect.ccli.com/Songs/456"
        )

    def test_returns_none_when_no_link(self):
        """Returns None when no link can be found."""
        el = MagicMock()
        el.get_attribute.return_value = None
        el.find_element.side_effect = Exception("no a tag")

        self.assertIsNone(self.extract_link(el))


class TestFindSongContainers(unittest.TestCase):
    """Tests for scraping_helpers.find_song_containers."""

    def setUp(self):
        from scraping_helpers import find_song_containers
        self.find = find_song_containers

    def test_finds_song_result_first(self):
        """Prefers 'song-result' class over 'song-item'."""
        mock_el = MagicMock()
        driver = MagicMock()
        driver.find_elements.side_effect = lambda by, cls: (
            [mock_el] if cls == "song-result" else []
        )
        result = self.find(driver)
        self.assertEqual(result, [mock_el])

    def test_falls_back_to_song_item(self):
        """Falls back to 'song-item' when 'song-result' not found."""
        mock_el = MagicMock()
        driver = MagicMock()
        driver.find_elements.side_effect = lambda by, cls: (
            [mock_el] if cls == "song-item" else []
        )
        result = self.find(driver)
        self.assertEqual(result, [mock_el])

    def test_returns_empty_when_nothing_found(self):
        """Returns empty list when no containers found."""
        driver = MagicMock()
        driver.find_elements.return_value = []
        result = self.find(driver)
        self.assertEqual(result, [])


class TestElementHasContent(unittest.TestCase):
    """Tests for scraping_helpers._element_has_content."""

    def setUp(self):
        from scraping_helpers import _element_has_content
        self.has_content = _element_has_content

    def test_true_when_text_present(self):
        el = MagicMock()
        el.text = "Amazing Grace"
        self.assertTrue(self.has_content(el))

    def test_true_when_textContent_present(self):
        el = MagicMock()
        el.text = ""
        el.get_attribute.return_value = "Hidden Content"
        self.assertTrue(self.has_content(el))

    def test_true_when_child_a_has_href(self):
        child_a = MagicMock()
        child_a.get_attribute.return_value = "https://example.com/song/1"

        el = MagicMock()
        el.text = ""
        el.get_attribute.return_value = ""
        el.find_element.return_value = child_a
        self.assertTrue(self.has_content(el))

    def test_false_when_empty(self):
        el = MagicMock()
        el.text = ""
        el.get_attribute.return_value = ""
        el.find_element.side_effect = Exception("no a tag")
        self.assertFalse(self.has_content(el))

    def test_false_when_whitespace_only(self):
        el = MagicMock()
        el.text = "   "
        el.get_attribute.return_value = "   "
        el.find_element.side_effect = Exception("no a tag")
        self.assertFalse(self.has_content(el))


class TestSongResultsPopulated(unittest.TestCase):
    """Tests for scraping_helpers.song_results_populated (WebDriverWait condition)."""

    def setUp(self):
        from scraping_helpers import song_results_populated
        self.populated = song_results_populated

    def test_returns_elements_when_populated(self):
        """Returns list of elements when first container has content."""
        mock_el = MagicMock()
        mock_el.text = "Way Maker by Sinach"

        driver = MagicMock()
        driver.find_elements.side_effect = lambda by, cls: (
            [mock_el] if cls == "song-result" else []
        )
        result = self.populated(driver)
        self.assertEqual(result, [mock_el])

    def test_returns_false_when_containers_empty(self):
        """Returns False when containers exist but have no content."""
        mock_el = MagicMock()
        mock_el.text = ""
        mock_el.get_attribute.return_value = ""
        mock_el.find_element.side_effect = Exception("no a tag")

        driver = MagicMock()
        driver.find_elements.side_effect = lambda by, cls: (
            [mock_el] if cls == "song-item" else []
        )
        result = self.populated(driver)
        self.assertFalse(result)

    def test_returns_false_when_no_containers(self):
        """Returns False when no containers exist at all."""
        driver = MagicMock()
        driver.find_elements.return_value = []
        result = self.populated(driver)
        self.assertFalse(result)

    def test_falls_back_to_second_class_when_first_empty(self):
        """Falls back to song-item class when song-result containers are empty."""
        empty_el = MagicMock()
        empty_el.text = ""
        empty_el.get_attribute.return_value = ""
        empty_el.find_element.side_effect = Exception("no a tag")

        populated_el = MagicMock()
        populated_el.text = "10,000 Reasons"

        driver = MagicMock()
        driver.find_elements.side_effect = lambda by, cls: (
            [empty_el] if cls == "song-result"
            else [populated_el] if cls == "song-item"
            else []
        )
        result = self.populated(driver)
        self.assertEqual(result, [populated_el])

    def test_uses_textContent_fallback(self):
        """Detects content via textContent when .text is empty."""
        mock_el = MagicMock()
        mock_el.text = ""
        mock_el.get_attribute.return_value = "Way Maker"

        driver = MagicMock()
        driver.find_elements.side_effect = lambda by, cls: (
            [mock_el] if cls == "song-result" else []
        )
        result = self.populated(driver)
        self.assertEqual(result, [mock_el])


if __name__ == "__main__":
    unittest.main()

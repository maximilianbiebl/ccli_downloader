"""
Browser utility functions for CCLI SongSelect Downloader.

Provides Chrome version detection and browser creation helpers to avoid
ChromeDriver/Chrome version mismatch errors.
"""

import re
import subprocess
import sys

import undetected_chromedriver as uc


def detect_chrome_version():
    """
    Detect the installed Chrome browser's major version number.

    Tries platform-specific methods to find Chrome and extract its version.

    Returns:
        int or None: The major version number (e.g., 145), or None if
        Chrome is not found or version cannot be determined.
    """
    commands = []

    if sys.platform.startswith("win"):
        commands = [
            [
                "reg", "query",
                r"HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon",
                "/v", "version",
            ],
            ["chrome", "--version"],
            [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "--version",
            ],
            [
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                "--version",
            ],
        ]
    elif sys.platform == "darwin":
        commands = [
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "--version",
            ],
            ["google-chrome", "--version"],
        ]
    else:
        # Linux
        commands = [
            ["google-chrome", "--version"],
            ["google-chrome-stable", "--version"],
            ["chromium-browser", "--version"],
            ["chromium", "--version"],
        ]

    for cmd in commands:
        try:
            output = subprocess.check_output(
                cmd, stderr=subprocess.DEVNULL, text=True
            )
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", output)
            if match:
                return int(match.group(1))
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            continue

    return None


def create_chrome(options=None, headless=False):
    """
    Create an undetected Chrome browser instance with automatic version matching.

    Detects the installed Chrome version and passes it as `version_main` to
    avoid ChromeDriver version mismatch errors.

    Parameters
    ----------
    options : uc.ChromeOptions, optional
        Chrome options to customize browser behavior.
    headless : bool, optional
        Whether to run the browser in headless mode. Default is False.

    Returns
    -------
    uc.Chrome
        A configured Chrome WebDriver instance.

    Raises
    ------
    RuntimeError
        If Chrome is not installed or the version cannot be detected.
    """
    version = detect_chrome_version()

    if version:
        print(f"Detected Chrome version: {version}")
    else:
        print("Warning: Could not detect Chrome version. Attempting default...")

    kwargs = {}
    if options:
        kwargs["options"] = options
    if headless:
        kwargs["headless"] = True
    if version:
        kwargs["version_main"] = version

    return uc.Chrome(**kwargs)

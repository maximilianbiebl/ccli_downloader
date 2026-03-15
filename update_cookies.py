"""
Cookie Update Tool for CCLI SongSelect.

Opens a browser window for manual login, extracts the required cookies,
and saves them to Cookie.txt and RequestVerificationToken.txt for future use.

Usage:
    python update_cookies.py
"""

import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

COOKIE_FILE = "Cookie.txt"
TOKEN_FILE = "RequestVerificationToken.txt"

REQUIRED_COOKIES = [
    "ARRAffinity",
    "ARRAffinitySameSite",
    "CCLI_AUTH",
    "CCLI_JWT_AUTH",
    ".AspNetCore.Session",
]
ANTIFORGERY_COOKIE_PREFIX = ".AspNetCore.Antiforgery"

LOGIN_URL = "https://reporting.ccli.com/search"
LOGIN_TIMEOUT = 300  # seconds to wait for manual login


def are_cookies_captured(cookies):
    """Check if all required cookies have been captured."""
    cookie_names = [c["name"] for c in cookies]
    for req in REQUIRED_COOKIES:
        if req not in cookie_names:
            return False
    if not any(c["name"].startswith(ANTIFORGERY_COOKIE_PREFIX) for c in cookies):
        return False
    return True


def extract_required_cookies(cookies):
    """Extract only the required cookies from the full cookie list."""
    cookies_dict = {}
    for c in cookies:
        name = c["name"]
        value = c["value"]
        if name in REQUIRED_COOKIES or name.startswith(ANTIFORGERY_COOKIE_PREFIX):
            cookies_dict[name] = value
    return cookies_dict


def get_verification_token(cookies):
    """Fetch the RequestVerificationToken using the captured cookies."""
    url = "https://reporting.ccli.com/api/antiForgery"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://reporting.ccli.com/",
        "Content-Type": "application/json;charset=utf-8",
    }
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        if response.status_code == 200:
            return response.text.strip('"')
    except Exception as e:
        print(f"Error fetching verification token: {e}")
    return None


def save_cookies(cookie_string, token):
    """Save cookies and token to files."""
    with open(COOKIE_FILE, "w") as f:
        f.write(cookie_string)

    with open(TOKEN_FILE, "w") as f:
        f.write(token)

    print(f"Cookies saved to {COOKIE_FILE}")
    print(f"Token saved to {TOKEN_FILE}")


def run_cookie_update():
    """Open browser for manual login and extract cookies."""
    driver = None
    try:
        print("=" * 50)
        print("CCLI Cookie Update Tool")
        print("=" * 50)
        print()
        print("A browser window will open.")
        print("Please log in to your CCLI account manually.")
        print(f"You have {LOGIN_TIMEOUT} seconds to complete the login.")
        print()

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        driver.get(LOGIN_URL)

        print("Waiting for login to complete...")

        # Wait until the URL contains the search page (post-login)
        WebDriverWait(driver, LOGIN_TIMEOUT).until(
            EC.url_contains("reporting.ccli.com/search")
        )
        print("Login detected!")

        # Capture all cookies
        cookies = driver.get_cookies()

        if not are_cookies_captured(cookies):
            print("Warning: Not all required cookies were captured.")
            print("The login may not have completed successfully.")
            return False

        filtered_cookies = extract_required_cookies(cookies)

        # Fetch the RequestVerificationToken
        token = get_verification_token(filtered_cookies)

        if not token:
            print("Warning: Could not retrieve RequestVerificationToken.")
            print("Some features may not work correctly.")

        # Build cookie string and save
        cookie_string = "; ".join(
            [f"{name}={value}" for name, value in filtered_cookies.items()]
        )

        save_cookies(cookie_string, token or "")

        print()
        print("Cookie update completed successfully!")
        print("You can now run the application with: python start.py")
        return True

    except Exception as e:
        print(f"Error during cookie update: {e}")
        return False
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    run_cookie_update()

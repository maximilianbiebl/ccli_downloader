import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from get_cookies_and_token import get_cookie_and_token


def execute_login():
    """
    Launch a browser using undetected-chromedriver and set cookies from Cookie.txt.

    Uses undetected-chromedriver to bypass Cloudflare Turnstile bot detection.

    Returns a WebDriver instance logged into SongSelect,
    or None if login fails.
    """
    driver = None
    try:
        # Step 1: Load cookies from file
        print("Loading cookies from file...")
        token, cookie = get_cookie_and_token()

        if not cookie:
            print("Login failed. No valid cookies found.")
            print("Please run 'python update_cookies.py' to log in and save cookies.")
            return None

        # Step 2: Launch browser with undetected-chromedriver
        print("Launching browser...")
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(options=options, headless=True)

        # Step 3: Navigate to root domain to set cookies
        print("Navigating to https://ccli.com...")
        driver.get("https://ccli.com")

        # Step 4: Set cookies from file
        print("Setting session cookies...")
        cookies = cookie.split("; ")
        for c in cookies:
            try:
                c = c.strip()
                if c.endswith(";"):
                    c = c[:-1]
                name, value = c.split("=", 1)
                driver.add_cookie({"name": name, "value": value, "domain": ".ccli.com"})
            except ValueError:
                print(f"Skipping malformed cookie: {c}")
            except Exception as e:
                print(f"Error setting cookie '{c}': {e}")

        # Step 5: Navigate to SongSelect
        print("Navigating to https://songselect.ccli.com...")
        driver.get("https://songselect.ccli.com")

        WebDriverWait(driver, 10).until(EC.url_contains("songselect.ccli.com"))
        print("SongSelect opened successfully!")

        return driver

    except Exception as e:
        print(f"An error occurred during login: {e}")
        print("Your cookies may have expired. Run 'python update_cookies.py' to refresh.")
        if driver:
            driver.quit()
        return None

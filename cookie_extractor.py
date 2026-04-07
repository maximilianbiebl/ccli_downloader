import sys
import time
import requests

try:
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError as e:
    print(f"Error: Missing dependency – {e}")
    print()
    print("Please install all required packages by running:")
    print()
    print("    python -m pip install -r requirements.txt")
    print()
    print("Note: use 'python -m pip' (not just 'pip') to make sure packages are")
    print("installed for the same Python interpreter that runs this script.")
    print("Do NOT copy package folders into the project directory.")
    sys.exit(1)

# Optional: import credentials
import variables  # enthält ccli_userame und ccli_password

required_cookies = [
    "ARRAffinity",
    "ARRAffinitySameSite",
    "CCLI_AUTH",
    "CCLI_JWT_AUTH",
    ".AspNetCore.Session",
]
antiforgery_cookie_prefix = ".AspNetCore.Antiforgery"


def are_cookies_captured(cookies):
    cookie_names = [c["name"] for c in cookies]
    for req in required_cookies:
        if req not in cookie_names:
            return False
    if not any(c["name"].startswith(antiforgery_cookie_prefix) for c in cookies):
        return False
    return True


def extract_required_cookies(cookies):
    cookies_dict = {}
    for c in cookies:
        name = c["name"]
        value = c["value"]
        if name in required_cookies or name.startswith(antiforgery_cookie_prefix):
            cookies_dict[name] = value
    return cookies_dict


def getVerificationToken(cookies):
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
        print(f"Fehler beim Abrufen des Tokens: {e}")
    return None


def gui_login():
    global driver
    filtered_cookies = {}
    request_verification_token = None

    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # optional, besser deaktivieren für manuelles Login
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get("https://reporting.ccli.com/search")

    print("Bitte logge dich manuell ein. Warte bis zur Dashboard-Seite...")

    # Warten, bis die URL die Suche enthält (nach manuellem Login)
    WebDriverWait(driver, 300).until(EC.url_contains("reporting.ccli.com/search"))
    print("Login erkannt!")

    # Alle Cookies erfassen
    cookies = driver.get_cookies()
    filtered_cookies = extract_required_cookies(cookies)

    # RequestVerificationToken abrufen
    request_verification_token = getVerificationToken(filtered_cookies)

    driver.quit()

    cookie_string = "; ".join([f"{name}={value}" for name, value in filtered_cookies.items()]) + ";"
    return request_verification_token, cookie_string


if __name__ == "__main__":
    token, cookie = gui_login()
    print("Token:", token)
    print("Cookie:", cookie)

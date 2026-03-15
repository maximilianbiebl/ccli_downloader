import os

COOKIE_FILE = "Cookie.txt"
TOKEN_FILE = "RequestVerificationToken.txt"


def validate_cookies(cookie_string):
    """Basic validation that the cookie string contains expected cookies."""
    required = ["CCLI_JWT_AUTH", "ARRAffinity"]
    for name in required:
        if name not in cookie_string:
            return False
    # Warn if cf_clearance is missing (Cloudflare protection cookie)
    if "cf_clearance" not in cookie_string:
        print("Warning: cf_clearance cookie not found. Cloudflare may block requests.")
        print("Run 'python update_cookies.py' to capture fresh cookies including Cloudflare tokens.")
    return True


def get_cookie_and_token():
    """
    Load cookies and token from Cookie.txt and RequestVerificationToken.txt.

    If the files do not exist or are invalid, instructs the user to run
    update_cookies.py to perform a manual login and save fresh cookies.

    Returns:
        tuple: (RequestVerificationToken, Cookie) strings
    """
    print("Loading cookies and token from files...")

    if not os.path.exists(COOKIE_FILE):
        print(f"Error: {COOKIE_FILE} not found.")
        print("Please run 'python update_cookies.py' to log in and save cookies.")
        return None, None

    if not os.path.exists(TOKEN_FILE):
        print(f"Error: {TOKEN_FILE} not found.")
        print("Please run 'python update_cookies.py' to log in and save cookies.")
        return None, None

    with open(TOKEN_FILE, "r") as f:
        token = f.read().strip()

    with open(COOKIE_FILE, "r") as f:
        cookie = f.read().strip()

    if not cookie:
        print(f"Error: {COOKIE_FILE} is empty.")
        print("Please run 'python update_cookies.py' to refresh your cookies.")
        return None, None

    if not validate_cookies(cookie):
        print("Error: Cookie.txt does not contain all required cookies.")
        print("Please run 'python update_cookies.py' to refresh your cookies.")
        return None, None

    print("Cookies and token loaded successfully.")
    return token, cookie

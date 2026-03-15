"""
Cookie extractor module for CCLI SongSelect.

This module is now superseded by update_cookies.py.
It is kept for backward compatibility but delegates to update_cookies.
"""

from update_cookies import run_cookie_update


def gui_login():
    """
    Open browser for manual login and extract cookies.

    Deprecated: Use update_cookies.run_cookie_update() instead.
    """
    print("Note: gui_login() is deprecated. Use 'python update_cookies.py' instead.")
    success = run_cookie_update()
    if success:
        with open("Cookie.txt", "r") as f:
            cookie_string = f.read().strip()
        with open("RequestVerificationToken.txt", "r") as f:
            token = f.read().strip()
        return token, cookie_string
    return None, None


if __name__ == "__main__":
    token, cookie = gui_login()
    if token:
        print("Token:", token)
        print("Cookie:", cookie)
    else:
        print("Cookie extraction failed.")

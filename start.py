import os
import tkinter as tk

from search_save import SongSelectApp

COOKIE_FILE = "Cookie.txt"


def main():
    driver = None

    # Try to login with existing cookies
    if os.path.exists(COOKIE_FILE):
        print("Cookies found. Attempting login...")
        try:
            from login_module import execute_login
            driver = execute_login()
        except Exception as e:
            print(f"Login with saved cookies failed: {e}")
            driver = None
    else:
        print("No cookies found. You can log in via the GUI.")

    # Launch GUI — works with or without an active driver
    print("Launching GUI...")
    root = tk.Tk()
    app = SongSelectApp(root, driver)
    root.mainloop()


if __name__ == "__main__":
    main()

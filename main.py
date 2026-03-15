from login_module import execute_login
from search_save import SongSelectApp
import tkinter as tk
import sys


def main():
    print("Attempting login with saved cookies...")
    driver = execute_login()

    if driver is None:
        print("Login failed. Cannot start the application.")
        print("Please run 'python update_cookies.py' to log in and save cookies.")
        sys.exit(1)

    print("Launching search and save GUI...")
    root = tk.Tk()
    app = SongSelectApp(root, driver)
    root.mainloop()


if __name__ == "__main__":
    main()

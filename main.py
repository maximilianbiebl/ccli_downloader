from login_module import execute_login
from search_save import SongSelectApp
import tkinter as tk


def main():
    print("Attempting login with saved cookies...")
    driver = execute_login()

    if driver is None:
        print("Login failed. Starting GUI without active session.")
        print("You can log in via the GUI.")

    print("Launching search and save GUI...")
    root = tk.Tk()
    app = SongSelectApp(root, driver)
    root.mainloop()


if __name__ == "__main__":
    main()

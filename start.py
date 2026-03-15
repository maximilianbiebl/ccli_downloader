import os
import subprocess

COOKIE_FILE = "Cookie.txt"


def main():
    if not os.path.exists(COOKIE_FILE):
        print("No cookies found. You need to log in first.")
        print("Launching cookie update tool...")
        subprocess.run(["python", "update_cookies.py"])

        # After cookie update, check if cookies were saved successfully
        if not os.path.exists(COOKIE_FILE):
            print("Cookie update was not completed. Exiting.")
            return

    print("Cookies found. Starting main application...")
    subprocess.run(["python", "main.py"])


if __name__ == "__main__":
    main()

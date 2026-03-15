import tkinter as tk
from tkinter import messagebox, filedialog
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

from settings import load_settings, save_settings as persist_settings
from lyrics_processing import process_lyrics_file

SONGSELECT_URL = "https://songselect.ccli.com"


class SongSelectApp:
    def __init__(self, root, driver=None):
        self.root = root
        self.root.title("SongSelect Automation")
        self.driver = driver
        self.song_links = []
        self.settings = load_settings()

        # Ensure the output folder exists
        output_folder = self.settings["output_folder"]
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Configure download folder if driver is ready
        if self.driver:
            self.configure_download_folder()

        # Create GUI elements
        self.create_widgets()

        # Update login status display
        self.update_login_status()

    def configure_download_folder(self):
        """Configure browser to download files into the desired folder."""
        folder = os.path.abspath(self.settings["output_folder"])
        params = {"behavior": "allow", "downloadPath": folder}
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", params)

    def create_widgets(self):
        # --- Login Section ---
        login_frame = tk.LabelFrame(self.root, text="Login", padx=10, pady=5)
        login_frame.pack(fill="x", padx=10, pady=5)

        self.login_button = tk.Button(
            login_frame, text="Login / Refresh Cookies", command=self.do_login
        )
        self.login_button.pack(side="left", padx=5)

        self.login_status_label = tk.Label(
            login_frame, text="Status: Not logged in", fg="red"
        )
        self.login_status_label.pack(side="left", padx=10)

        # --- Settings Section ---
        settings_frame = tk.LabelFrame(self.root, text="Settings", padx=10, pady=5)
        settings_frame.pack(fill="x", padx=10, pady=5)

        # Output Folder
        folder_frame = tk.Frame(settings_frame)
        folder_frame.pack(fill="x", pady=2)
        tk.Label(folder_frame, text="Output Folder:").pack(side="left")
        self.folder_var = tk.StringVar(value=self.settings["output_folder"])
        self.folder_entry = tk.Entry(
            folder_frame, textvariable=self.folder_var, width=30
        )
        self.folder_entry.pack(side="left", padx=5)
        tk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(
            side="left"
        )

        # Line Separator
        sep_frame = tk.Frame(settings_frame)
        sep_frame.pack(fill="x", pady=2)
        tk.Label(sep_frame, text="Line Separator:").pack(side="left")
        self.separator_var = tk.StringVar(value=self.settings["line_separator"])
        self.separator_entry = tk.Entry(
            sep_frame, textvariable=self.separator_var, width=10
        )
        self.separator_entry.pack(side="left", padx=5)

        # Lines per Slide
        lines_frame = tk.Frame(settings_frame)
        lines_frame.pack(fill="x", pady=2)
        tk.Label(lines_frame, text="Lines per Slide:").pack(side="left")
        self.lines_var = tk.StringVar(value=str(self.settings["lines_per_slide"]))
        self.lines_entry = tk.Entry(lines_frame, textvariable=self.lines_var, width=5)
        self.lines_entry.pack(side="left", padx=5)

        # Save Settings button
        tk.Button(
            settings_frame, text="Save Settings", command=self.save_settings
        ).pack(pady=5)

        # --- Search Section ---
        search_frame = tk.LabelFrame(self.root, text="Search", padx=10, pady=5)
        search_frame.pack(fill="x", padx=10, pady=5)

        search_input_frame = tk.Frame(search_frame)
        search_input_frame.pack(fill="x")
        tk.Label(search_input_frame, text="Search for Songs:").pack(side="left")
        self.search_entry = tk.Entry(search_input_frame, width=40)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda _: self.perform_search())

        button_frame = tk.Frame(search_frame)
        button_frame.pack(fill="x", pady=5)
        self.search_button = tk.Button(
            button_frame, text="Search", command=self.perform_search
        )
        self.search_button.pack(side="left", padx=5)
        self.reset_button = tk.Button(
            button_frame, text="Reset Search", command=self.reset_search
        )
        self.reset_button.pack(side="left", padx=5)

        # --- Results Section ---
        results_frame = tk.LabelFrame(
            self.root, text="Search Results", padx=10, pady=5
        )
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.results_listbox = tk.Listbox(results_frame, height=15, width=60)
        self.results_listbox.pack(fill="both", expand=True, pady=5)

        # --- Action Buttons ---
        action_frame = tk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=5)
        self.save_song_button = tk.Button(
            action_frame, text="Save Song", command=self.save_song
        )
        self.save_song_button.pack(side="left", padx=5)
        self.quit_button = tk.Button(
            action_frame, text="Quit", command=self.quit_application
        )
        self.quit_button.pack(side="right", padx=5)

    # ------------------------------------------------------------------
    # Login helpers
    # ------------------------------------------------------------------

    def update_login_status(self):
        """Update the login status indicator."""
        if self.driver:
            self.login_status_label.config(
                text="Status: Logged in \u2713", fg="green"
            )
        else:
            self.login_status_label.config(
                text="Status: Not logged in \u2717", fg="red"
            )

    def do_login(self):
        """Trigger the cookie update process and then create a browser session."""
        from update_cookies import run_cookie_update
        from login_module import execute_login

        self.login_status_label.config(text="Status: Logging in\u2026", fg="orange")
        self.root.update()

        success = run_cookie_update()
        if not success:
            messagebox.showerror(
                "Login Failed",
                "Cookie update was not completed.\nPlease try again.",
            )
            self.update_login_status()
            return

        driver = execute_login()
        if driver:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.driver = driver
            self.configure_download_folder()
            self.update_login_status()
            messagebox.showinfo("Success", "Login successful!")
        else:
            messagebox.showerror(
                "Login Failed",
                "Could not establish browser session.\nPlease try again.",
            )
            self.update_login_status()

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    def browse_folder(self):
        """Open a folder browser dialog."""
        folder = filedialog.askdirectory(
            initialdir=self.settings["output_folder"]
        )
        if folder:
            self.folder_var.set(folder)
            self.save_settings()

    def save_settings(self):
        """Persist current GUI settings to disk."""
        try:
            lines_per_slide = int(self.lines_var.get())
            if lines_per_slide < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid Setting", "Lines per Slide must be a positive integer."
            )
            return

        self.settings["output_folder"] = self.folder_var.get()
        self.settings["line_separator"] = self.separator_var.get()
        self.settings["lines_per_slide"] = lines_per_slide

        persist_settings(self.settings)

        output_folder = self.settings["output_folder"]
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if self.driver:
            self.configure_download_folder()

        print("Settings saved.")

    # ------------------------------------------------------------------
    # Search & save
    # ------------------------------------------------------------------

    def perform_search(self):
        if not self.driver:
            messagebox.showwarning("Not Logged In", "Please log in first.")
            return

        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Error", "Please enter a search query.")
            return

        try:
            # Auto-clear previous results
            self.results_listbox.delete(0, tk.END)
            self.song_links.clear()

            print(f"Initiating search for: {query}")

            # Navigate to the search page for a clean state
            self.driver.get(SONGSELECT_URL)

            # Locate the search bar and enter the query
            search_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "SearchTextInput-1"))
            )
            search_input.clear()
            search_input.send_keys(query)
            search_input.send_keys("\n")

            print("Waiting for search results to load...")

            # Wait for search results to appear
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "song-item"))
            )
            print("Search results loaded successfully!")
            self.display_search_results()
        except Exception as e:
            print(f"Error during search: {e}")
            error_msg = str(e).lower()
            if "timeout" in error_msg or "no such" in error_msg:
                result = messagebox.askyesno(
                    "Session Error",
                    "The search failed. Your session may have expired.\n\n"
                    "Would you like to re-login?",
                )
                if result:
                    self.do_login()
            else:
                messagebox.showerror("Error", f"Failed to perform search: {e}")

    def display_search_results(self):
        try:
            songs = self.driver.find_elements(By.CLASS_NAME, "song-item")
            self.results_listbox.delete(0, tk.END)
            self.song_links.clear()

            for song in songs:
                try:
                    title = song.find_element(By.CLASS_NAME, "title").text
                    authors = song.find_element(By.CLASS_NAME, "authors").text
                    link = song.get_attribute("href")
                    self.results_listbox.insert(tk.END, f"{title} by {authors}")
                    self.song_links.append(link)
                except Exception as e:
                    print(f"Error parsing song element: {e}")
        except Exception as e:
            print("Error retrieving search results.")
            messagebox.showerror(
                "Error", f"Failed to retrieve search results: {e}"
            )

    def save_song(self):
        if not self.driver:
            messagebox.showwarning("Not Logged In", "Please log in first.")
            return

        try:
            selected_index = self.results_listbox.curselection()
            if not selected_index:
                messagebox.showwarning("Error", "Please select a song.")
                return

            # Persist settings so the latest values are used
            self.save_settings()

            output_folder = os.path.abspath(self.settings["output_folder"])
            files_before = (
                set(os.listdir(output_folder))
                if os.path.exists(output_folder)
                else set()
            )

            # Navigate to the lyrics page
            link = self.song_links[selected_index[0]]
            lyrics_link = link + "/viewlyrics"
            self.driver.get(lyrics_link)

            # Wait for the download button
            download_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "lyricsDownloadButton"))
            )
            download_button.click()

            # Wait for the download to complete
            print("Downloading lyrics file...")
            time.sleep(5)

            # Find and post-process newly downloaded files
            files_after = set(os.listdir(output_folder))
            new_files = files_after - files_before

            for new_file in new_files:
                if new_file.endswith(".txt"):
                    filepath = os.path.join(output_folder, new_file)
                    process_lyrics_file(
                        filepath,
                        self.settings.get("line_separator", "//"),
                        self.settings.get("lines_per_slide", 2),
                    )

            messagebox.showinfo("Status", "Song lyrics downloaded successfully.")
        except Exception as e:
            print(f"Error during song save: {e}")
            error_msg = str(e).lower()
            if "timeout" in error_msg or "no such" in error_msg:
                result = messagebox.askyesno(
                    "Session Error",
                    "The save failed. Your session may have expired.\n\n"
                    "Would you like to re-login?",
                )
                if result:
                    self.do_login()
            else:
                messagebox.showerror("Error", f"Failed to save song: {e}")

    def reset_search(self):
        """Reset the search fields and results."""
        self.search_entry.delete(0, tk.END)
        self.results_listbox.delete(0, tk.END)
        self.song_links.clear()
        print("Search reset successfully.")

    def quit_application(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    print("This script should not be run directly.")

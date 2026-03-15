# CCLI SongSelect Downloader

A tool to download song lyrics from [CCLI SongSelect](https://songselect.ccli.com) for import into presentation software like [FreeShow](https://freeshow.app).

## Features

- **Search & Download** – Search for songs by title or lyrics directly from the GUI and download them as text files.
- **FreeShow-Compatible Formatting** – Section labels (Verse 1, Chorus, Bridge, etc.) are wrapped in square brackets and merged with the first lyrics line, e.g. `[Verse 1] I lay my life down`.
- **Configurable Line Separators** – Insert a custom separator (e.g. `//`) or empty lines after every *N* content lines for slide-based presentation software.
- **Lines per Slide** – Choose how many lyrics lines appear between separators (default: 2).
- **Filename Line Count** – Optionally append `_2-zeilig` (or the configured count) to the filename.
- **Include Metadata** – Optionally keep the song title, author, copyright (©) and CCLI number in the output file. Metadata is added *after* separator processing so it does not affect slide breaks.
- **Persistent Settings** – All preferences (output folder, separator, lines per slide, flags) are saved to `settings.json` and restored on next launch.
- **Login from GUI** – Log in or refresh cookies directly from the application without restarting.

## Requirements

- Python 3.8+
- Google Chrome browser
- A valid CCLI SongSelect account

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Setup: Cookie-Based Login

This tool uses cookies from a manual browser login to authenticate with SongSelect. No passwords are stored in files.

The browser uses [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) to bypass Cloudflare Turnstile bot detection that protects the CCLI website.

### Step 1: Save your login cookies

Run the cookie update tool:

```bash
python update_cookies.py
```

A browser window will open. Log in to your CCLI account manually. Once logged in, the tool will automatically extract and save the required cookies (including Cloudflare tokens) to `Cookie.txt`.

### Step 2: Start the application

```bash
python start.py
```

The application will load your saved cookies and open the song search GUI.

### Refreshing Cookies

Cookies expire over time. If you get authentication errors or Cloudflare blocking messages, simply re-run:

```bash
python update_cookies.py
```

Or click **Login / Refresh Cookies** in the GUI.

## Settings

All settings are configurable in the GUI and saved to `settings.json`.

| Setting | Default | Description |
|---------|---------|-------------|
| Output Folder | `./songs` | Directory where downloaded lyrics files are saved |
| Line Separator | `//` | String inserted between slide groups (e.g. `//`, `---`) |
| Use Empty Lines | off | Use blank lines as separators instead of the separator string |
| Lines per Slide | `2` | Number of content lines between separators |
| Add to Filename | off | Append `_N-zeilig` to the filename (e.g. `Way Maker_2-zeilig.txt`) |
| Include Metadata | off | Keep song title, author, © and CCLI number in the output |

## Required Cookies

The following cookies are extracted during login:

| Cookie | Purpose |
|--------|---------|
| `CCLI_JWT_AUTH` | JWT authentication token |
| `CCLI_AUTH` | Session authentication |
| `ARRAffinity` / `ARRAffinitySameSite` | Azure load balancer affinity |
| `.AspNetCore.Session` | Server-side session |
| `.AspNetCore.Antiforgery.*` | CSRF protection |
| `cf_clearance` | Cloudflare bot protection clearance |

## Project Structure

| File | Description |
|------|-------------|
| `start.py` | Entry point – checks for cookies and launches the app |
| `main.py` | Alternative entry point – initializes browser and GUI |
| `search_save.py` | Song search and download GUI (tkinter) |
| `settings.py` | Settings persistence (`settings.json`) |
| `lyrics_processing.py` | Lyrics post-processing: section label merging, separators, metadata |
| `scraping_helpers.py` | Search result scraping with multi-selector fallback |
| `login_module.py` | Sets saved cookies on undetected browser |
| `get_cookies_and_token.py` | Loads cookies and token from files |
| `update_cookies.py` | Cookie update tool – manual browser login |
| `browser_utils.py` | Chrome version detection and browser creation helpers |
| `cookie_extractor.py` | Legacy wrapper (delegates to `update_cookies.py`) |

## Running Tests

```bash
python -m unittest tests.test_cookies -v
```

## Troubleshooting

### ChromeDriver version mismatch

If you see an error like `This version of ChromeDriver only supports Chrome version X`, the tool will now auto-detect your installed Chrome version and download the matching ChromeDriver. Make sure Google Chrome is installed and up to date.

### Cloudflare Turnstile errors (Error 600010)

If you see errors like `[Cloudflare Turnstile] Error: 600010` or MIME type errors, your cookies have expired or were not captured correctly. Run `python update_cookies.py` to refresh them.

### CSS / MIME type errors

Errors like `Refused to apply style ... MIME type ('text/html')` indicate Cloudflare is blocking the browser. This is resolved by using undetected-chromedriver and fresh cookies.

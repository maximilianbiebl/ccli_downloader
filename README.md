# CCLI SongSelect Downloader

A tool to download song lyrics from [CCLI SongSelect](https://songselect.ccli.com) for import into programs like [FreeShow](https://freeshow.app).

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

### Step 1: Save your login cookies

Run the cookie update tool:

```bash
python update_cookies.py
```

A browser window will open. Log in to your CCLI account manually. Once logged in, the tool will automatically extract and save the required cookies to `Cookie.txt`.

### Step 2: Start the application

```bash
python start.py
```

The application will load your saved cookies and open the song search GUI.

### Refreshing Cookies

Cookies expire over time. If you get authentication errors, simply re-run:

```bash
python update_cookies.py
```

## Required Cookies

The following cookies are extracted during login:

| Cookie | Purpose |
|--------|---------|
| `CCLI_JWT_AUTH` | JWT authentication token |
| `CCLI_AUTH` | Session authentication |
| `ARRAffinity` / `ARRAffinitySameSite` | Azure load balancer affinity |
| `.AspNetCore.Session` | Server-side session |
| `.AspNetCore.Antiforgery.*` | CSRF protection |

## Project Structure

| File | Description |
|------|-------------|
| `start.py` | Entry point - checks for cookies and launches the app |
| `main.py` | Main application - initializes browser and GUI |
| `login_module.py` | Sets saved cookies on headless browser |
| `get_cookies_and_token.py` | Loads cookies and token from files |
| `update_cookies.py` | Cookie update tool - manual browser login |
| `search_save.py` | Song search and download GUI |
| `cookie_extractor.py` | Legacy wrapper (delegates to update_cookies.py) |

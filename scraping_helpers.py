"""Helper functions for scraping SongSelect search results.

Extracted from search_save.py for testability (no tkinter dependency).
"""

from selenium.webdriver.common.by import By

# CSS class selectors to try for finding song result containers (in order)
SONG_CONTAINER_CLASSES = ["song-result", "song-item"]

# Strategies to extract the song title from within a song result element.
# Each entry is (By strategy, selector string).
TITLE_SELECTORS = [
    (By.CSS_SELECTOR, ".song-result-title a"),
    (By.CSS_SELECTOR, ".song-result-title"),
    (By.CLASS_NAME, "title"),
    (By.CSS_SELECTOR, "[class*='title']"),
]

# Strategies to extract the song author from within a song result element.
AUTHOR_SELECTORS = [
    (By.CSS_SELECTOR, ".song-result-subtitle"),
    (By.CLASS_NAME, "authors"),
    (By.CLASS_NAME, "author"),
    (By.CSS_SELECTOR, "[class*='subtitle']"),
    (By.CSS_SELECTOR, "[class*='author']"),
]


def try_extract_text(parent, selectors):
    """Try multiple selectors to extract non-empty text from a parent element.

    Args:
        parent: A Selenium WebElement to search within.
        selectors: List of (By strategy, selector string) tuples.

    Returns:
        The first non-empty text found, or "".
    """
    for by_strategy, selector in selectors:
        try:
            el = parent.find_element(by_strategy, selector)
            text = el.text.strip()
            if text:
                return text
            # .text can be empty for hidden elements; try textContent
            text = (el.get_attribute("textContent") or "").strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def try_extract_link(element):
    """Extract the song link from an element or its child <a> tag.

    Args:
        element: A Selenium WebElement.

    Returns:
        The href string, or None if not found.
    """
    link = element.get_attribute("href")
    if link:
        return link
    try:
        a_el = element.find_element(By.TAG_NAME, "a")
        return a_el.get_attribute("href")
    except Exception:
        return None


def find_song_containers(driver):
    """Find song result container elements, trying multiple class names.

    Args:
        driver: A Selenium WebDriver instance.

    Returns:
        A list of WebElements, or an empty list.
    """
    for cls in SONG_CONTAINER_CLASSES:
        songs = driver.find_elements(By.CLASS_NAME, cls)
        if songs:
            print(f"Found {len(songs)} results using container class '{cls}'")
            return songs
    return []

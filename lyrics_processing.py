"""Lyrics post-processing utilities for CCLI SongSelect Downloader.

Provides functions to insert line separators into downloaded lyrics files
for use with presentation software.
"""

import os


def process_lyrics_file(filepath, separator="//", lines_per_slide=2):
    """Insert line separators into a lyrics file for presentation software.

    Counts non-empty lines and inserts the *separator* after every
    *lines_per_slide* non-empty lines.

    Parameters
    ----------
    filepath : str
        Path to the lyrics text file.
    separator : str
        The separator string to insert (e.g. "//" or "---").
    lines_per_slide : int
        Number of non-empty content lines between separators.
    """
    if not separator or lines_per_slide < 1:
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        processed = []
        content_line_count = 0

        for line in lines:
            processed.append(line)
            if line.strip():
                content_line_count += 1
                if content_line_count % lines_per_slide == 0:
                    processed.append(separator)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(processed))

        print(
            f"Added '{separator}' every {lines_per_slide} lines "
            f"to {os.path.basename(filepath)}"
        )
    except Exception as e:
        print(f"Error processing lyrics file: {e}")

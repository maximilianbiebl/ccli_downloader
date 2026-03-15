"""Lyrics post-processing utilities for CCLI SongSelect Downloader.

Provides functions to insert line separators into downloaded lyrics files
for use with presentation software.
"""

import os


def process_lyrics_file(filepath, separator="//", lines_per_slide=2):
    """Insert line separators into a lyrics file for presentation software.

    Counts non-empty lines and inserts the *separator* after every
    *lines_per_slide* non-empty lines.  An empty string ``""`` is a valid
    separator and will insert blank lines.

    Parameters
    ----------
    filepath : str
        Path to the lyrics text file.
    separator : str or None
        The separator string to insert (e.g. ``"//"`` or ``"---"``).
        Use ``""`` to insert blank lines.  Pass *None* to skip processing.
    lines_per_slide : int
        Number of non-empty content lines between separators.
    """
    if separator is None or lines_per_slide < 1:
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

        sep_desc = "empty line" if separator == "" else f"'{separator}'"
        print(
            f"Added {sep_desc} every {lines_per_slide} lines "
            f"to {os.path.basename(filepath)}"
        )
    except Exception as e:
        print(f"Error processing lyrics file: {e}")


def rename_with_line_count(filepath, lines_per_slide):
    """Rename a lyrics file to include a ``_N-zeilig`` suffix.

    For example ``Way Maker.txt`` becomes ``Way Maker_2-zeilig.txt``.

    Parameters
    ----------
    filepath : str
        Path to the lyrics text file.
    lines_per_slide : int
        The line count to embed in the filename.

    Returns
    -------
    str
        The new filepath after renaming.
    """
    base, ext = os.path.splitext(filepath)
    new_path = f"{base}_{lines_per_slide}-zeilig{ext}"
    os.rename(filepath, new_path)
    print(f"Renamed to {os.path.basename(new_path)}")
    return new_path

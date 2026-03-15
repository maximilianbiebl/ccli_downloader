"""Lyrics post-processing utilities for CCLI SongSelect Downloader.

Provides functions to insert line separators into downloaded lyrics files
for use with presentation software.
"""

import os
import re

# Pattern matching common CCLI SongSelect section labels.
# Matches lines like "Verse 1", "Chorus", "Pre-Chorus 2", "Bridge", etc.
_SECTION_LABEL_RE = re.compile(
    r"^(Verse|Chorus|Bridge|Pre-Chorus|Tag|Ending|Intro|Interlude|Outro|Misc)"
    r"(\s+\d+)?$",
    re.IGNORECASE,
)


def is_section_label(line):
    """Return *True* if *line* looks like a CCLI section label.

    Examples: ``Verse 1``, ``Chorus``, ``Pre-Chorus 2``, ``Bridge``.
    """
    return bool(_SECTION_LABEL_RE.match(line.strip()))


def merge_section_labels(text):
    """Wrap section labels in brackets and merge them with the next content line.

    Transforms standalone section labels (e.g. ``Verse 1``) so that they
    appear on the same line as the first lyrics line that follows, wrapped
    in square brackets::

        Verse 1                  →  [Verse 1] I lay my life down
        I lay my life down

    This format is required by presentation software such as FreeShow.

    Parameters
    ----------
    text : str
        The raw lyrics content.

    Returns
    -------
    str
        The transformed lyrics content.
    """
    lines = text.splitlines()
    merged = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if is_section_label(stripped):
            label = f"[{stripped}]"
            # Look ahead for the next non-empty line to merge with
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines):
                merged.append(f"{label} {lines[i]}")
            else:
                # Label at end of file with no following content
                merged.append(label)
        else:
            merged.append(lines[i])
        i += 1
    return "\n".join(merged)


def merge_section_labels_file(filepath):
    """Apply :func:`merge_section_labels` to a file in-place.

    Parameters
    ----------
    filepath : str
        Path to the lyrics text file.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        merged = merge_section_labels(content)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(merged)

        print(f"Merged section labels in {os.path.basename(filepath)}")
    except Exception as e:
        print(f"Error merging section labels: {e}")


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

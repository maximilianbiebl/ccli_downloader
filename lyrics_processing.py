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

# Patterns that identify CCLI footer/metadata lines (author, copyright, licence).
_METADATA_RE = re.compile(
    r"©|CCLI[\s\-]|ccli\.com|SongSelect|All rights reserved",
    re.IGNORECASE,
)


def is_section_label(line):
    """Return *True* if *line* looks like a CCLI section label.

    Examples: ``Verse 1``, ``Chorus``, ``Pre-Chorus 2``, ``Bridge``.
    """
    return bool(_SECTION_LABEL_RE.match(line.strip()))


def is_metadata_line(line):
    """Return *True* if *line* looks like a CCLI footer/metadata line.

    Matches copyright notices (``©``), CCLI references, SongSelect
    licence text, and similar non-lyrics content that appears at the end
    of CCLI SongSelect download files.
    """
    return bool(_METADATA_RE.search(line))


def extract_metadata(text):
    """Extract title and footer metadata from raw CCLI lyrics text.

    The title is defined as the non-empty lines that appear *before* the
    first section label (e.g. ``Verse 1``).  Footer metadata consists of
    author names, copyright notices, and CCLI references at the end of
    the file.

    Parameters
    ----------
    text : str
        The raw lyrics content as downloaded from CCLI SongSelect.

    Returns
    -------
    tuple[list[str], list[str]]
        ``(title_lines, footer_lines)`` – lists of stripped, non-empty
        strings.  Either list may be empty if the corresponding section
        is absent.
    """
    lines = text.splitlines()

    # --- Locate first section label ---
    first_section = 0
    for idx, line in enumerate(lines):
        if is_section_label(line.strip()):
            first_section = idx
            break

    # --- Extract title lines (before first section label) ---
    title_lines = []
    for i in range(first_section):
        stripped = lines[i].strip()
        if stripped:
            title_lines.append(stripped)

    # --- Find footer metadata ---
    lyrics_lines = lines[first_section:]
    meta_start = len(lyrics_lines)
    for idx, line in enumerate(lyrics_lines):
        if is_metadata_line(line):
            meta_start = idx
            while meta_start > 0:
                prev = lyrics_lines[meta_start - 1].strip()
                if not prev or is_section_label(prev):
                    break
                meta_start -= 1
            break

    footer_lines = []
    for i in range(meta_start, len(lyrics_lines)):
        stripped = lyrics_lines[i].strip()
        if stripped:
            footer_lines.append(stripped)

    return title_lines, footer_lines


def add_metadata_to_file(filepath, title_lines, footer_lines):
    """Prepend title and append footer metadata to a processed lyrics file.

    This is intended to be called **after** :func:`process_lyrics_file` so
    that line separators are placed only between lyrics lines, and the
    metadata is added around them without affecting separator placement.

    Parameters
    ----------
    filepath : str
        Path to the lyrics text file (already processed).
    title_lines : list[str]
        Title lines to prepend.
    footer_lines : list[str]
        Footer metadata lines to append.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        parts = []
        if title_lines:
            parts.extend(title_lines)
            parts.append("")  # blank line after title

        # Add the existing processed content line-by-line
        parts.extend(content.splitlines())

        if footer_lines:
            parts.append("")  # blank line before footer
            parts.extend(footer_lines)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))

        print(f"Added metadata to {os.path.basename(filepath)}")
    except Exception as e:
        print(f"Error adding metadata: {e}")


def merge_section_labels(text, include_metadata=False):
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
    include_metadata : bool
        When *True*, the song title (lines before the first section label)
        and footer metadata (author, ©, CCLI number) are preserved in the
        output.  When *False* (the default) they are stripped.

    Returns
    -------
    str
        The transformed lyrics content.
    """
    lines = text.splitlines()

    # --- Locate first section label ---
    first_section = 0
    for idx, line in enumerate(lines):
        if is_section_label(line.strip()):
            first_section = idx
            break

    # --- Extract title lines (before first section label) ---
    title_lines = []
    if include_metadata:
        for i in range(first_section):
            stripped = lines[i].strip()
            if stripped:
                title_lines.append(stripped)

    # Strip everything before the first section label
    lines = lines[first_section:]

    # --- Strip footer metadata (author, ©, CCLI number, licence) ---
    # Find the first metadata-pattern line and walk backwards to include
    # any preceding non-blank lines in the same block (e.g. author names).
    meta_start = len(lines)
    footer_lines = []
    for idx, line in enumerate(lines):
        if is_metadata_line(line):
            meta_start = idx
            # Walk backwards over non-blank, non-section-label lines
            # that belong to the same metadata block.
            while meta_start > 0:
                prev = lines[meta_start - 1].strip()
                if not prev or is_section_label(prev):
                    break
                meta_start -= 1
            break

    if include_metadata:
        for i in range(meta_start, len(lines)):
            stripped = lines[i].strip()
            if stripped:
                footer_lines.append(stripped)

    lines = lines[:meta_start]

    # --- Merge section labels with the next content line and strip blanks ---
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
        elif stripped:
            # Only keep non-empty lines; blank lines from the source are
            # discarded so that process_lyrics_file can place separators
            # at the correct positions.
            merged.append(lines[i])
        i += 1

    # --- Assemble final output ---
    result_parts = []
    if title_lines:
        result_parts.extend(title_lines)
        result_parts.append("")  # blank line after title
    result_parts.extend(merged)
    if footer_lines:
        result_parts.append("")  # blank line before footer
        result_parts.extend(footer_lines)

    return "\n".join(result_parts)


def merge_section_labels_file(filepath, include_metadata=False):
    """Apply :func:`merge_section_labels` to a file in-place.

    Parameters
    ----------
    filepath : str
        Path to the lyrics text file.
    include_metadata : bool
        When *True*, preserve the song title and footer metadata in the
        output.  See :func:`merge_section_labels` for details.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        merged = merge_section_labels(content, include_metadata=include_metadata)

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

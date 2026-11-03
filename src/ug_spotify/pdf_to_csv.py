from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any

import pdfplumber


DATE_RE = re.compile(
    r"^(?:\d+\s+days?\s+ago|[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})$"
)


def _text(words: list[dict[str, Any]]) -> str:
    return " ".join(str(word["text"]) for word in sorted(words, key=lambda word: word["x0"]))


def convert_pdf(source: Path, destination: Path) -> int:
    """Convert a text-based Ultimate Guitar My Tabs PDF export to CSV."""
    rows: list[dict[str, str]] = []
    saw_header = False

    with pdfplumber.open(str(source)) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            grouped: list[list[dict[str, Any]]] = []
            for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
                if grouped and abs(grouped[-1][0]["top"] - word["top"]) <= 2:
                    grouped[-1].append(word)
                else:
                    grouped.append([word])

            for line_words in grouped:
                artist_words = [word for word in line_words if 155 <= word["x0"] < 300]
                song_words = [word for word in line_words if 300 <= word["x0"] < 610]
                date_words = [word for word in line_words if 610 <= word["x0"] < 700]
                type_words = [word for word in line_words if 700 <= word["x0"] < 760]
                whole_line = _text(line_words)
                if "ARTIST SONG DATE TYPE" in whole_line:
                    saw_header = True
                    continue
                if not saw_header:
                    continue

                tab_type = _text(type_words)
                if tab_type not in {"Chords", "Ukulele"}:
                    continue
                saved_date = _text(date_words)
                if not DATE_RE.fullmatch(saved_date):
                    continue
                title = _text(song_words).strip()
                if not title:
                    continue
                rows.append(
                    {
                        "title": title,
                        "artist": _text(artist_words).strip(),
                        "saved_date": saved_date,
                        "tab_type": tab_type,
                    }
                )

    if not saw_header:
        raise ValueError("This PDF does not look like an Ultimate Guitar My Tabs export.")
    if not rows:
        raise ValueError("No song rows were extracted. The PDF may be scanned or formatted differently.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["title", "artist", "saved_date", "tab_type"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a text-based Ultimate Guitar My Tabs PDF export to CSV."
    )
    parser.add_argument("pdf_file", type=Path)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output CSV path (default: PDF path with .csv suffix)",
    )
    args = parser.parse_args(argv)
    output = args.output or args.pdf_file.with_suffix(".csv")
    try:
        count = convert_pdf(args.pdf_file, output)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"Converted {count} songs to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

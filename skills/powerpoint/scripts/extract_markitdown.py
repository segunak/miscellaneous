#!/usr/bin/env python3
"""Extract PowerPoint content with MarkItDown when it is installed.

Use this as a fallback or second opinion when python-pptx extraction misses
content from unusual layouts, grouped shapes, comments, or embedded objects.
"""
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def convert(filepath):
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "MarkItDown is not installed. Run: python scripts\\setup_deps.py --full"
        ) from exc

    converter = MarkItDown()
    result = converter.convert(str(filepath))
    text = getattr(result, "text_content", None)
    if text is None:
        text = getattr(result, "markdown", None)
    if text is None:
        text = str(result)
    return text


def main():
    parser = argparse.ArgumentParser(description="Extract PowerPoint content with MarkItDown")
    parser.add_argument("file", help="PowerPoint file path")
    parser.add_argument("--output", help="Optional output markdown/text file")
    args = parser.parse_args()

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    try:
        text = convert(filepath)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Run content and structural QA checks for a PowerPoint deck."""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.dom import minidom

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_pptx import analyze
from extract_text import extract
from inspect_pptx import inspect as inspect_deck
from ooxml_pptx import validate_pptx

DEFAULT_PLACEHOLDER_PATTERN = r"\b(lorem|ipsum|todo|tbd|xxxx+|placeholder|sample text|click to add|this\s+(page|slide)\s+layout)\b"


def scan_text(text, pattern):
    regex = re.compile(pattern, re.IGNORECASE)
    matches = []
    for match in regex.finditer(text or ""):
        start = max(match.start() - 45, 0)
        end = min(match.end() + 45, len(text))
        matches.append({"match": match.group(0), "context": text[start:end].replace("\n", " ")})
    return matches


def scan_xml(pptx_path, pattern):
    regex = re.compile(pattern, re.IGNORECASE)
    hits = []
    with zipfile.ZipFile(pptx_path, "r") as archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            if not (re.fullmatch(r"ppt/slides/slide\d+\.xml", name) or re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)):
                continue
            try:
                xml = archive.read(name).decode("utf-8", errors="ignore")
                dom = minidom.parseString(xml)
            except Exception:
                continue
            for node in dom.getElementsByTagName("*"):
                if node.localName != "t" or not node.firstChild:
                    continue
                text = node.firstChild.nodeValue or ""
                for match in regex.finditer(text):
                    start = max(match.start() - 60, 0)
                    end = min(match.end() + 60, len(text))
                    hits.append({"part": name, "match": match.group(0), "context": text[start:end]})
                    if len(hits) >= 200:
                        return hits
    return hits


def run_qa(pptx_path, pattern):
    extracted = extract(str(pptx_path), fmt="text", include_notes=True)
    inspection = inspect_deck(str(pptx_path), include_text=True, include_notes=True)
    analysis = analyze(str(pptx_path), verbose=False)
    validation = validate_pptx(pptx_path)
    text_placeholders = scan_text(extracted, pattern)
    xml_placeholders = scan_xml(pptx_path, pattern)

    issues = []
    if not validation.get("valid"):
        issues.append({"severity": "error", "issue": "OOXML structural validation failed", "details": validation.get("errors", [])})
    if text_placeholders or xml_placeholders:
        issues.append({"severity": "warning", "issue": "Potential placeholder text found"})
    for item in analysis.get("issues", []):
        if item.get("severity") in {"warning", "error"}:
            issues.append(item)

    return {
        "ok": not any(issue.get("severity") == "error" for issue in issues),
        "file": str(pptx_path),
        "slide_count": inspection.get("total_slides"),
        "validation": validation,
        "analysis_stats": analysis.get("stats", {}),
        "analysis_issues": analysis.get("issues", []),
        "placeholder_scan": {
            "pattern": pattern,
            "text_hits": text_placeholders,
            "xml_hits": xml_placeholders,
        },
        "qa_issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Run PowerPoint QA checks")
    parser.add_argument("pptx", help="PowerPoint file to check")
    parser.add_argument("--placeholder-pattern", default=DEFAULT_PLACEHOLDER_PATTERN)
    parser.add_argument("--strict", action="store_true", help="Return nonzero when warnings are found")
    args = parser.parse_args()

    pptx_path = Path(args.pptx)
    if not pptx_path.exists():
        print(json.dumps({"ok": False, "error": f"File not found: {pptx_path}"}, indent=2))
        return 1

    result = run_qa(pptx_path, args.placeholder_pattern)
    print(json.dumps(result, indent=2, default=str))
    if args.strict and result["qa_issues"]:
        return 1
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
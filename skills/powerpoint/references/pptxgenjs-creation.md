# PptxGenJS Creation Reference

Use PptxGenJS when the task is to create a polished presentation from scratch. Keep the existing Python tools for reading, analysis, simple edits, and OOXML repair.

## Setup

From the skill folder:

```powershell
python scripts\setup_deps.py --full
node scripts\check_pptxgenjs_env.js
```

If only Node dependencies are needed:

```powershell
python scripts\setup_deps.py --node
```

## Generator Workflow

1. Write a short design plan: audience, setting, tone, dominant palette, visual motif, and slide pattern mix.
2. Create a deck spec JSON file.
3. Generate the deck with PptxGenJS.
4. Run content and structural QA.
5. Export slide images on Windows when visual inspection matters.
6. Fix the deck and re-run QA.

Commands:

```powershell
node scripts\create_pptxgenjs_deck.js references\pptxgenjs-sample-deck.json output.pptx
python scripts\qa_pptx.py output.pptx
powershell -ExecutionPolicy Bypass -File scripts\export_slides_windows.ps1 -PptxPath output.pptx -OutputDir rendered
```

The export script uses installed Microsoft PowerPoint through Windows automation. It is optional and should be used for final visual review when available.

## Deck Spec Shape

```json
{
  "title": "Deck title",
  "subtitle": "Deck subtitle",
  "author": "Author",
  "theme": {
    "colors": {
      "primary": "0F766E",
      "secondary": "155E75",
      "accent": "F97316",
      "background": "F8FAFC",
      "surface": "FFFFFF",
      "text": "0F172A",
      "muted": "64748B",
      "inverse": "FFFFFF",
      "line": "CBD5E1"
    },
    "fonts": {
      "heading": "Aptos Display",
      "body": "Aptos"
    }
  },
  "slides": [
    { "type": "title", "title": "Title", "subtitle": "Subtitle" },
    { "type": "bullets", "title": "Key Points", "items": ["One", "Two"] },
    { "type": "closing", "title": "Thank you" }
  ]
}
```

Supported slide types in `scripts/create_pptxgenjs_deck.js`:

| Type | Use |
|------|-----|
| `title` | Opening slide with strong first impression |
| `section` | Major transition or topic shift |
| `bullets` | Short key points with a visual side panel |
| `twoColumn` / `comparison` | Before and after, option tradeoffs, paired concepts |
| `process` | Sequential loop, lifecycle, or workflow |
| `iconGrid` | Related concepts with icons and short copy |
| `quote` | Memorable claim or external authority |
| `chart` | Bar, line, pie, or doughnut data |
| `table` | Structured comparison or rubric |
| `image` | Large image plus optional text panel |
| `closing` | Final call to action or takeaway |

## Design Rules

- Choose one dominant color, one support color, and one accent.
- Pick a motif that repeats across the deck: side bars, icon bubbles, cards, half-bleed images, or numbered process blocks.
- Vary slide patterns. Do not create a deck that is only title plus bullets.
- Give every slide a visual job: compare, sequence, classify, quantify, quote, show, or summarize.
- Keep body text left aligned. Center only short titles, labels, or intentionally sparse statements.
- Use strong size contrast: title 34-48pt, section labels 18-24pt, body 12-20pt depending on density.
- Keep at least 0.5 inches of edge margin and use consistent gaps between blocks.
- Avoid low-contrast text, decorative clutter, and tiny labels.

## PptxGenJS Pitfalls

- Use 6-character hex colors without `#`. Do not use 8-character hex colors for opacity.
- Use opacity or transparency options instead of encoding alpha in color strings.
- Use `bullet: true` for bullets. Do not type bullet characters into strings.
- Use `breakLine: true` between rich text runs that should appear on separate lines.
- Do not reuse mutable option objects across shapes. Create a fresh object each time.
- Set `margin: 0` when text must align exactly with shapes or icons.
- Use image `sizing` for contain or cover behavior so images do not distort.
- Prefer chart styling options over default chart output.
- Use slide masters and helper functions so typography, colors, and spacing remain consistent.

## Icons

The generator uses `react-icons` plus `sharp` to render crisp PNG icons. Use icon names such as `FaCheckCircle`, `FaRoute`, `FaTools`, or `FaQuoteRight` in slide specs. If icon dependencies are not installed, the generator falls back to a simple text mark inside the icon bubble.

## Charts

For chart slides, provide labels and one or more series:

```json
{
  "type": "chart",
  "title": "Where Autonomy Helps",
  "chartType": "bar",
  "labels": ["Search", "Drafting", "Coding", "Ops"],
  "series": [{ "name": "Fit", "values": [55, 70, 82, 64] }]
}
```

The generator applies the deck palette, muted axes, subtle gridlines, and data labels by default.

## QA Loop

Always run:

```powershell
python scripts\qa_pptx.py output.pptx
```

When PowerPoint is installed on Windows and visual quality matters, also run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\export_slides_windows.ps1 -PptxPath output.pptx -OutputDir rendered
```

Inspect exported slide images for overlap, clipped text, awkward wrapping, uneven spacing, low contrast, leftover placeholders, and layouts that feel too repetitive. Fix issues and re-run QA.
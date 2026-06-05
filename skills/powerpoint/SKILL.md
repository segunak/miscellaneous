---
name: powerpoint
description: "Use this skill whenever a PowerPoint, PPTX, slide deck, presentation, slides, pitch deck, or .pptx/.pptm/.ppt file is involved as input or output. This includes reading, extracting, summarizing, searching, comparing, inspecting, analyzing, reviewing, editing, restructuring, creating, or repairing PowerPoint files; working with speaker notes, tables, charts, images, layouts, templates, Office Open XML, or deck metadata; and producing content that will become slides. Trigger even if the user only says deck, slides, presentation, or references a PowerPoint filename casually."
---

# PowerPoint Skill

## Setup (First Use)

```bash
python3 scripts/setup_deps.py
```
Installs the core dependencies: python-pptx, Pillow, and pyyaml. Skip if already installed.

For optional MarkItDown fallback extraction and PptxGenJS deck generation:

```bash
python3 scripts/setup_deps.py --full
```

For only the local Node dependencies used by PptxGenJS:

```bash
python3 scripts/setup_deps.py --node
node scripts/check_pptxgenjs_env.js
```

On Windows, use `python` if `python3` is not available:

```powershell
python scripts\setup_deps.py
python scripts\setup_deps.py --full
python scripts\setup_deps.py --node
```

## Workflow Decision Tree

1. **Read or summarize a deck**: Run `scripts/extract_text.py deck.pptx --notes`, then synthesize the content. Use `scripts/extract_markitdown.py` as a fallback or second pass when extraction looks incomplete.
2. **Compare two decks**: Run `scripts/extract_text.py` on both decks, inspect both structures, then compare structure, repeated sections, missing slides, audience fit, and speaker notes.
3. **Inspect structure**: Run `scripts/inspect_pptx.py` for slide count, dimensions, layouts, shapes, images, charts, tables, and notes metadata.
4. **Analyze and suggest improvements**: Run `scripts/analyze_pptx.py` and provide prioritized findings with slide references.
5. **Create a polished new presentation**: Use PptxGenJS with `scripts/create_pptxgenjs_deck.js` and `references/pptxgenjs-creation.md`. This is the preferred path for decks made from scratch.
6. **Create a quick functional presentation**: Use python-pptx when polish is not the priority or the task needs a small utilitarian file.
7. **Edit simple content**: Use python-pptx for direct text, table, chart, image, and notes edits when the formatting can be preserved safely.
8. **Restructure or template-edit**: Use `scripts/ooxml_pptx.py` to unpack, list, add-slide, clean, pack, and validate Office Open XML when changing slide order, duplicating layouts, removing orphaned parts, or repairing files.

## Quick-Start Scripts

Run these commands from the skill folder so relative `scripts/` paths resolve. Use absolute paths for PowerPoint files outside the skill folder.

Slide numbers in script inputs and outputs are 1-based and match PowerPoint's slide numbers.

## Reading Presentations

When the user asks to read, summarize, search, compare, or understand a PowerPoint deck:

1. Run `scripts/extract_text.py deck.pptx --notes` to capture slide text, tables, and speaker notes.
2. Run `scripts/extract_markitdown.py deck.pptx` if the first extraction appears incomplete, if the deck has unusual layouts, or if the user asks for maximum text capture.
3. Run `scripts/inspect_pptx.py deck.pptx` when slide count, layouts, shapes, images, charts, or table metadata matter.
4. Run `scripts/analyze_pptx.py deck.pptx` when the user asks for quality feedback or improvement suggestions.
5. Synthesize the extracted content in normal language. Reference slide numbers when calling out specific sections.

Recommended commands:

```bash
python3 scripts/extract_text.py deck.pptx --notes
python3 scripts/extract_markitdown.py deck.pptx
python3 scripts/inspect_pptx.py deck.pptx --text --notes
python3 scripts/analyze_pptx.py deck.pptx
```

Windows equivalents:

```powershell
python scripts\extract_text.py "C:\path\to\deck.pptx" --notes
python scripts\extract_markitdown.py "C:\path\to\deck.pptx"
python scripts\inspect_pptx.py "C:\path\to\deck.pptx" --text --notes
python scripts\analyze_pptx.py "C:\path\to\deck.pptx"
```

### Inspect File Structure
```bash
python3 scripts/inspect_pptx.py deck.pptx                    # Overview
python3 scripts/inspect_pptx.py deck.pptx --text              # With all text
python3 scripts/inspect_pptx.py deck.pptx --notes             # With speaker notes
python3 scripts/inspect_pptx.py deck.pptx --layouts           # With layout details
python3 scripts/inspect_pptx.py deck.pptx --slide 1           # Single slide, 1-based
python3 scripts/inspect_pptx.py deck.pptx --text --notes      # Full content
```
Returns JSON: slide count, dimensions, shapes, text, images, charts, tables, notes.

### Extract Text
```bash
python3 scripts/extract_text.py deck.pptx                     # Markdown format
python3 scripts/extract_text.py deck.pptx --format json        # Structured JSON
python3 scripts/extract_text.py deck.pptx --format text        # Plain text
python3 scripts/extract_text.py deck.pptx --notes              # Include speaker notes
python3 scripts/extract_markitdown.py deck.pptx                # Optional fallback extractor
```

### Analyze & Improve
```bash
python3 scripts/analyze_pptx.py deck.pptx                     # Full analysis
python3 scripts/analyze_pptx.py deck.pptx --verbose            # Extra detail
```
Returns JSON with stats (fonts, sizes, layouts, text density) and issues (readability, consistency, missing notes, visual balance).

### OOXML Utilities
```bash
python3 scripts/ooxml_pptx.py validate deck.pptx
python3 scripts/ooxml_pptx.py list deck.pptx
python3 scripts/ooxml_pptx.py unpack deck.pptx unpacked --pretty-xml
python3 scripts/ooxml_pptx.py add-slide unpacked slide2.xml
python3 scripts/ooxml_pptx.py add-slide unpacked slideLayout3.xml --position 5
python3 scripts/ooxml_pptx.py clean unpacked
python3 scripts/ooxml_pptx.py pack unpacked output.pptx --original deck.pptx
```

Windows equivalents:

```powershell
python scripts\ooxml_pptx.py validate "C:\path\to\deck.pptx"
python scripts\ooxml_pptx.py list "C:\path\to\deck.pptx"
python scripts\ooxml_pptx.py unpack "C:\path\to\deck.pptx" unpacked --pretty-xml
python scripts\ooxml_pptx.py add-slide unpacked slide2.xml
python scripts\ooxml_pptx.py clean unpacked
python scripts\ooxml_pptx.py pack unpacked output.pptx --original "C:\path\to\deck.pptx"
```

Use these for structural operations such as slide order, raw XML review, template cleanup, and validation. Do not use them for ordinary text replacement when python-pptx can safely do the job.

### PptxGenJS Creation

Use this lane for polished decks created from scratch:

```bash
python3 scripts/setup_deps.py --full
node scripts/check_pptxgenjs_env.js
node scripts/create_pptxgenjs_deck.js references/pptxgenjs-sample-deck.json output.pptx
python3 scripts/qa_pptx.py output.pptx
```

Windows equivalents:

```powershell
python scripts\setup_deps.py --full
node scripts\check_pptxgenjs_env.js
node scripts\create_pptxgenjs_deck.js references\pptxgenjs-sample-deck.json output.pptx
python scripts\qa_pptx.py output.pptx
```

Optional visual export on Windows when Microsoft PowerPoint is installed:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\export_slides_windows.ps1 -PptxPath output.pptx -OutputDir rendered
```

## Creating Presentations

### Preferred Path: Polished Decks with PptxGenJS

Use PptxGenJS when the user wants a new deck that should look designed, modern, or presentation-ready.

Before writing code, always create a concise design plan:

1. Audience, setting, and tone.
2. Topic-specific palette with one dominant color, one support color, and one accent.
3. Repeated visual motif such as icon bubbles, side bars, process blocks, cards, or half-bleed images.
4. Slide pattern mix: title, section, comparison, process, quote, chart or table, and closing.
5. QA loop: text extraction, structural validation, placeholder scan, and visual inspection when available.

Then create a spec JSON and generate the deck:

```powershell
node scripts\create_pptxgenjs_deck.js my-deck-spec.json output.pptx
python scripts\qa_pptx.py output.pptx
```

Use `references/pptxgenjs-creation.md` for slide types, design rules, icon usage, chart styling, and PptxGenJS pitfalls.

### Design Principles
Before writing code, always:
1. **Analyze content**: What topic, tone, audience, and setting?
2. **Choose palette**: See `references/design-and-creation.md` for curated palettes and layout guidance.
3. **Plan layout**: Decide slide types: title, content, section, comparison, quote, chart, scenario, closing.
4. **State approach**: Explain design choices before implementation

### Key Rules
- Use **web-safe fonts only**: Arial, Verdana, Georgia, Tahoma, Trebuchet MS, Times New Roman, Courier New
- Create **clear visual hierarchy** through size, weight, and color
- Keep **text concise**: aim for 6 or fewer bullet points and short bullet text
- Ensure **strong contrast** between text and backgrounds
- Use **consistent spacing** and alignment across all slides
- Vary layouts. Do not repeat the same title-and-bullets structure for every slide.
- Give each slide a visual job: comparison, diagram, quote, chart, image, icon row, process flow, or scenario prompt.
- Add **speaker notes** for presentation delivery

### Quick Functional python-pptx Template

Use this only when a simple functional deck is sufficient or when Python interoperability is more important than visual polish.

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Title slide
slide = prs.slides.add_slide(prs.slide_layouts[0])
slide.shapes.title.text = "Title"
slide.placeholders[1].text = "Subtitle"

# Content slide
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Section"
body = slide.placeholders[1].text_frame
body.text = "First point"
p = body.add_paragraph()
p.text = "Second point"
p.level = 0

prs.save("output.pptx")
```

For full creation reference (PptxGenJS, shapes, formatting, charts, tables, images, notes) see `references/design-and-creation.md` and `references/pptxgenjs-creation.md`.

## Editing Presentations

### Simple Edits (python-pptx)
```python
from pptx import Presentation

prs = Presentation("existing.pptx")
slide = prs.slides[0]

for shape in slide.shapes:
    if shape.has_text_frame:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                run.text = run.text.replace("old", "new")

prs.save("modified.pptx")
```

### Advanced Edits (OOXML)
For operations beyond python-pptx (animations, slide order, template restructuring, complex formatting, raw XML manipulation), use `scripts/ooxml_pptx.py` and see `references/ooxml-editing.md`.

Recommended structural workflow:

1. Validate the original file.
2. Unpack the file with `--pretty-xml` if manual XML edits are expected.
3. List slide order and identify the exact slide XML files to edit.
4. Make all structural changes first: delete slide IDs, duplicate slides or layouts with `add-slide`, and reorder slide IDs.
5. Make targeted XML edits.
6. For large template updates, use subagents only after the structure is stable; give each subagent exact slide XML files and formatting rules.
7. Clean orphaned slide, notes, and media parts.
8. Pack to a new `.pptx` with `--original`.
9. Validate and run `scripts/qa_pptx.py`.

## Providing Improvement Feedback

When asked to review or improve a presentation:

1. Run `scripts/inspect_pptx.py deck.pptx --text --notes`
2. Run `scripts/analyze_pptx.py deck.pptx`
3. Present findings in this order:
   - **Overview**: slide count, layout types, visual balance
   - **Content Issues**: text density, empty slides, missing titles
   - **Design Issues**: font consistency, size readability, color contrast
   - **Structure Issues**: flow, pacing, section organization
   - **Suggestions**: specific actionable improvements with slide references

## QA Expectations

Before declaring a deck edit complete:

1. Run `scripts/qa_pptx.py output.pptx` for extraction, analysis, placeholder scanning, and OOXML validation.
2. Run `scripts/extract_text.py output.pptx --notes` when you need to manually inspect narrative order and speaker notes.
3. Run `scripts/inspect_pptx.py output.pptx --text --notes` for structural sanity.
4. Run `scripts/analyze_pptx.py output.pptx` for text density, missing titles, font consistency, and notes coverage.
5. Run `scripts/ooxml_pptx.py validate output.pptx` after OOXML edits or after generating a deck.
6. When visual quality matters and Microsoft PowerPoint is available on Windows, export slide images with `scripts/export_slides_windows.ps1` and inspect for overlap, clipping, low contrast, repeated layouts, awkward wrapping, and broken alignment.
7. Fix issues and re-run the checks. Do not declare a polished generated deck complete after the first pass if QA found problems.

## Common Slide Patterns

| Pattern | Layout | When to Use |
|---------|--------|-------------|
| Title Slide | Layout 0 | Opening, section dividers |
| Bullets | Layout 1 | Key points, agenda |
| Two-Column | Layout 3 | Comparison, before/after |
| Image + Text | Layout 5 + textbox | Visual storytelling |
| Chart Slide | Layout 5 + chart | Data presentation |
| Table Slide | Layout 5 + table | Structured data |
| Quote Slide | Layout 6 + textbox | Attribution, emphasis |
| Closing | Layout 0 or 6 | Thank you, contact info |

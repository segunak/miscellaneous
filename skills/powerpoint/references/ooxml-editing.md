# OOXML Editing Reference

For advanced PowerPoint editing that goes beyond python-pptx capabilities, work directly with the OOXML (Office Open XML) format.

## Table of Contents
1. [Unpack/Repack Workflow](#unpackrepack-workflow)
2. [Key File Paths](#key-file-paths)
3. [Common XML Patterns](#common-xml-patterns)
4. [Namespace Reference](#namespace-reference)

## Unpack/Repack Workflow

A .pptx file is a ZIP archive containing XML files.

Prefer the bundled helper for normal OOXML work:

```bash
python scripts/ooxml_pptx.py validate presentation.pptx
python scripts/ooxml_pptx.py unpack presentation.pptx unpacked --pretty-xml
python scripts/ooxml_pptx.py list unpacked
# Edit targeted XML files.
python scripts/ooxml_pptx.py clean unpacked
python scripts/ooxml_pptx.py pack unpacked modified.pptx --original presentation.pptx
python scripts/ooxml_pptx.py validate modified.pptx
```

Use manual ZIP commands only when the helper is unavailable.

```bash
# Unpack
mkdir unpacked && cd unpacked
unzip ../presentation.pptx

# Edit XML files as needed...

# Repack
zip -r ../modified.pptx . -x ".*"
```

Or use python:
```python
import zipfile, shutil
from pathlib import Path

# Unpack
def unpack(pptx_path, output_dir):
    with zipfile.ZipFile(pptx_path, 'r') as z:
        z.extractall(output_dir)

# Repack
def repack(input_dir, pptx_path):
    with zipfile.ZipFile(pptx_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in Path(input_dir).rglob('*'):
            if f.is_file():
                z.write(f, f.relative_to(input_dir))
```

## Key File Paths

| Path | Content |
|------|---------|
| `ppt/presentation.xml` | Main metadata, slide order |
| `ppt/slides/slide{N}.xml` | Individual slide content |
| `ppt/slides/_rels/slide{N}.xml.rels` | Slide relationships (images, layouts) |
| `ppt/slideMasters/slideMaster1.xml` | Master slide template |
| `ppt/slideLayouts/slideLayout{N}.xml` | Layout templates |
| `ppt/theme/theme1.xml` | Colors, fonts, theme info |
| `ppt/notesSlides/notesSlide{N}.xml` | Speaker notes |
| `ppt/media/` | Images and media files |
| `[Content_Types].xml` | MIME type declarations |

## Common XML Patterns

### Text Run
```xml
<a:r>
  <a:rPr lang="en-US" sz="1800" b="1" dirty="0"/>
  <a:t>Bold text at 18pt</a:t>
</a:r>
```
- `sz` = font size in hundredths of a point (1800 = 18pt)
- `b="1"` = bold, `i="1"` = italic, `u="sng"` = underline

### Color
```xml
<!-- Solid color fill -->
<a:solidFill>
  <a:srgbClr val="4472C4"/>
</a:solidFill>

<!-- Theme color -->
<a:solidFill>
  <a:schemeClr val="dk1"/>
</a:solidFill>
```

### Shape Position & Size
```xml
<a:xfrm>
  <a:off x="838200" y="365125"/>    <!-- Position in EMUs (1 inch = 914400 EMU) -->
  <a:ext cx="7772400" cy="1470025"/> <!-- Size in EMUs -->
</a:xfrm>
```

### Adding an Image
1. Copy image to `ppt/media/imageN.ext`
2. Add relationship in `ppt/slides/_rels/slideN.xml.rels`:
```xml
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/>
```
3. Reference in slide XML:
```xml
<p:pic>
  <p:nvPicPr>
    <p:cNvPr id="4" name="Picture 3"/>
    <p:cNvPicPr/>
    <p:nvPr/>
  </p:nvPicPr>
  <p:blipFill>
    <a:blip r:embed="rId2"/>
    <a:stretch><a:fillRect/></a:stretch>
  </p:blipFill>
  <p:spPr>
    <a:xfrm>
      <a:off x="914400" y="914400"/>
      <a:ext cx="5486400" cy="3657600"/>
    </a:xfrm>
    <a:prstGeom prst="rect"/>
  </p:spPr>
</p:pic>
```

## Namespace Reference

```
xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
```

Common prefix usage:
- `a:` = DrawingML (text, shapes, colors, fonts)
- `p:` = PresentationML (slides, transitions, notes)
- `r:` = Relationships (links between parts)

## Template Editing Workflow

When adapting an existing deck as a template:

1. Extract text and notes with `scripts/extract_text.py`.
2. Inspect structure with `scripts/inspect_pptx.py --text --notes --layouts`.
3. Unpack the deck with `scripts/ooxml_pptx.py unpack --pretty-xml`.
4. List the slide order with `scripts/ooxml_pptx.py list`.
5. Choose source slides by layout and purpose, not just by position.
6. Make all structural changes first: remove unwanted slide IDs, duplicate slides or layouts with `add-slide`, and reorder slide IDs in `ppt/presentation.xml`.
7. Edit slide XML only after the structure is stable.
8. For large decks, split slide XML files across subagents only after step 6. Give each subagent exact slide files, target content, and formatting rules.
9. Clean, pack, validate, run `scripts/qa_pptx.py`, then extract text again to check content.

Keep edits targeted. Do not rewrite the entire XML file when a small text, relationship, or slide order change is enough.

## Slide Operations

Slide order lives in `ppt/presentation.xml` under `<p:sldIdLst>`.

To reorder slides, move the relevant `<p:sldId>` elements. The slide XML files do not need to be renamed.

To remove a slide, remove its `<p:sldId>` entry, then run:

```bash
python scripts/ooxml_pptx.py clean unpacked
```

The cleanup step removes unreferenced slide files, slide relationships, notes slides, and media that no remaining relationship references.

To add a slide by copying another slide or creating a slide from a layout, use the helper:

```powershell
python scripts\ooxml_pptx.py add-slide unpacked slide2.xml
python scripts\ooxml_pptx.py add-slide unpacked slideLayout3.xml --position 5
```

The helper creates the slide part, updates relationships, updates `[Content_Types].xml`, copies notes for duplicated slides, and inserts the slide in `ppt/presentation.xml` unless `--no-insert` is used.

When packing, XML is condensed in the packaged copy by default so the source folder can remain readable while the final package is compact:

```powershell
python scripts\ooxml_pptx.py pack unpacked output.pptx --original template.pptx
```

Use `--no-condense-xml` only when debugging exact XML whitespace.

## Editing Text Safely

PowerPoint text is usually stored in `<a:t>` elements inside runs:

```xml
<a:r>
  <a:rPr lang="en-US" sz="1800" b="1"/>
  <a:t>Slide text</a:t>
</a:r>
```

Guidelines:

- Preserve the surrounding `<a:rPr>` formatting unless you intentionally want a style change.
- For multiple bullets or separate ideas, use separate `<a:p>` paragraphs instead of joining everything into one long string.
- Use XML escaping for `&`, `<`, and `>`.
- Use `xml:space="preserve"` on `<a:t>` when leading or trailing spaces matter.
- After editing, run `scripts/ooxml_pptx.py validate` and `scripts/extract_text.py` on the packed deck.

## Common Pitfalls

- Do not rename slide XML files just to reorder slides. Reorder `<p:sldId>` entries instead.
- Do not delete slide XML files without also removing references from `ppt/presentation.xml` and related `.rels` files.
- Do not clear text from unused template elements and leave empty boxes behind. Remove the unused shape when possible.
- Do not assume a visual edit worked because XML validates. Validation catches structural problems, not bad design.
- Do not use OOXML for simple text replacement unless python-pptx cannot preserve what you need.
- Do not leave placeholder content in a template. Run `python scripts\qa_pptx.py output.pptx --strict` before declaring the deck complete.

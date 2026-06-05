#!/usr/bin/env python3
"""OOXML helpers for PowerPoint files.

This script intentionally avoids presentation rendering dependencies. It focuses
on safe ZIP extraction, slide-order inspection, basic cleanup, repacking, and
structural validation for .pptx files.
"""
import argparse
import json
import posixpath
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from xml.dom import minidom
from xml.parsers.expat import ExpatError

RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SLIDE_REL_SUFFIX = "/slide"
SLIDE_LAYOUT_REL_SUFFIX = "/slideLayout"
NOTES_REL_SUFFIX = "/notesSlide"

REL_TYPES = {
    "slide": f"{OFFICE_REL_NS}/slide",
    "slide_layout": f"{OFFICE_REL_NS}/slideLayout",
    "notes_slide": f"{OFFICE_REL_NS}/notesSlide",
}

CONTENT_TYPES = {
    "presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
    "slide": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
    "slide_layout": "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml",
    "slide_master": "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml",
    "notes_slide": "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
    "notes_master": "application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml",
    "theme": "application/vnd.openxmlformats-officedocument.theme+xml",
}

MEDIA_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "svg": "image/svg+xml",
    "emf": "image/x-emf",
    "wmf": "image/x-wmf",
}


def print_json(data):
    print(json.dumps(data, indent=2, default=str))


def normalize_zip_name(name):
    return name.replace("\\", "/")


def is_safe_zip_name(name):
    normalized = normalize_zip_name(name)
    parts = PurePosixPath(normalized).parts
    return (
        normalized
        and not normalized.startswith("/")
        and not re.match(r"^[A-Za-z]:", normalized)
        and ".." not in parts
    )


def safe_extract(pptx_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pptx_path, "r") as archive:
        for member in archive.infolist():
            if not is_safe_zip_name(member.filename):
                raise ValueError(f"Unsafe zip member path: {member.filename}")
            archive.extract(member, output_dir)


def parse_xml(path):
    return minidom.parse(str(path))


def write_dom(path, dom):
    path.write_text(dom.toxml(encoding="utf-8").decode("utf-8"), encoding="utf-8")


def new_relationships_dom():
    dom = minidom.Document()
    root = dom.createElement("Relationships")
    root.setAttribute("xmlns", RELS_NS)
    dom.appendChild(root)
    return dom


def elements_by_local_name(dom, local_name):
    return [node for node in dom.getElementsByTagName("*") if node.localName == local_name]


def relationship_map(rels_path):
    if not rels_path.exists():
        return {}

    dom = parse_xml(rels_path)
    rels = {}
    for rel in elements_by_local_name(dom, "Relationship"):
        rel_id = rel.getAttribute("Id")
        rels[rel_id] = {
            "id": rel_id,
            "type": rel.getAttribute("Type"),
            "target": rel.getAttribute("Target"),
            "target_mode": rel.getAttribute("TargetMode"),
        }
    return rels


def next_relationship_id(rels):
    highest = 0
    for rel_id in rels:
        match = re.fullmatch(r"rId(\d+)", rel_id)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"rId{highest + 1}"


def add_relationship(rels_path, rel_type, target):
    if rels_path.exists():
        dom = parse_xml(rels_path)
    else:
        rels_path.parent.mkdir(parents=True, exist_ok=True)
        dom = new_relationships_dom()
    rels = relationship_map(rels_path) if rels_path.exists() else {}
    rel_id = next_relationship_id(rels)
    root = dom.documentElement
    rel = dom.createElement("Relationship")
    rel.setAttribute("Id", rel_id)
    rel.setAttribute("Type", rel_type)
    rel.setAttribute("Target", target)
    root.appendChild(rel)
    write_dom(rels_path, dom)
    return rel_id


def resolve_part_target(source_part, target):
    if target.startswith("/"):
        return target.lstrip("/")
    source_dir = posixpath.dirname(source_part)
    return posixpath.normpath(posixpath.join(source_dir, target)).replace("\\", "/")


def rels_path_for_part(unpacked_dir, part_path):
    part = PurePosixPath(part_path)
    return unpacked_dir / str(part.parent) / "_rels" / f"{part.name}.rels"


def get_slide_order(unpacked_dir):
    pres_path = unpacked_dir / "ppt" / "presentation.xml"
    pres_rels_path = unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"
    if not pres_path.exists() or not pres_rels_path.exists():
        return []

    presentation_rels = relationship_map(pres_rels_path)
    dom = parse_xml(pres_path)
    slides = []
    for index, slide_id in enumerate(elements_by_local_name(dom, "sldId"), start=1):
        rel_id = slide_id.getAttributeNS(OFFICE_REL_NS, "id") or slide_id.getAttribute("r:id") or slide_id.getAttribute("id")
        rel = presentation_rels.get(rel_id, {})
        target = rel.get("target", "")
        part_path = resolve_part_target("ppt/presentation.xml", target) if target else ""
        slides.append(
            {
                "index": index,
                "slide_id": slide_id.getAttribute("id"),
                "relationship_id": rel_id,
                "target": target,
                "path": part_path,
                "exists": bool(part_path and (unpacked_dir / part_path).exists()),
                "hidden": slide_id.getAttribute("show") == "0",
            }
        )
    return slides


def extract_first_text(xml_path):
    if not xml_path.exists():
        return ""
    try:
        dom = parse_xml(xml_path)
    except Exception:
        return ""
    text_items = []
    for text_node in elements_by_local_name(dom, "t"):
        if text_node.firstChild and text_node.firstChild.nodeValue:
            text = text_node.firstChild.nodeValue.strip()
            if text:
                text_items.append(text)
    return " ".join(text_items)[:160]


def command_unpack(args):
    pptx_path = Path(args.pptx)
    output_dir = Path(args.output_dir)
    if not pptx_path.exists():
        print_json({"ok": False, "error": f"File not found: {pptx_path}"})
        return 1
    if output_dir.exists() and any(output_dir.iterdir()) and not args.overwrite:
        print_json({"ok": False, "error": f"Output directory is not empty: {output_dir}"})
        return 1
    if output_dir.exists() and args.overwrite:
        shutil.rmtree(output_dir)

    safe_extract(pptx_path, output_dir)
    xml_files_formatted = format_xml_tree(output_dir, pretty=True) if args.pretty_xml else 0
    slides = get_slide_order(output_dir)
    print_json({"ok": True, "output_dir": str(output_dir), "slides": len(slides), "xml_files_formatted": xml_files_formatted})
    return 0


def command_list(args):
    root = ensure_unpacked(Path(args.path))
    with root as unpacked_dir:
        slides = get_slide_order(unpacked_dir)
        for slide in slides:
            slide["first_text"] = extract_first_text(unpacked_dir / slide["path"])
        print_json({"ok": True, "slides": slides})
    return 0


class ensure_unpacked:
    def __init__(self, path):
        self.path = path
        self.temp_dir = None

    def __enter__(self):
        if self.path.is_dir():
            return self.path
        self.temp_dir = tempfile.TemporaryDirectory()
        safe_extract(self.path, Path(self.temp_dir.name))
        return Path(self.temp_dir.name)

    def __exit__(self, exc_type, exc, traceback):
        if self.temp_dir:
            self.temp_dir.cleanup()


def collect_relationship_targets(unpacked_dir):
    targets = set()
    for rels_file in unpacked_dir.rglob("*.rels"):
        rels_relative = rels_file.relative_to(unpacked_dir).as_posix()
        if "/_rels/" not in rels_relative:
            continue
        source_dir, rels_name = rels_relative.split("/_rels/", 1)
        source_part = f"{source_dir}/{rels_name[:-5]}"
        try:
            rels = relationship_map(rels_file)
        except Exception:
            continue
        for rel in rels.values():
            target = rel.get("target", "")
            if target and rel.get("target_mode") != "External":
                targets.add(resolve_part_target(source_part, target))
    return targets


def remove_content_type_overrides(unpacked_dir, deleted_paths):
    content_types = unpacked_dir / "[Content_Types].xml"
    if not content_types.exists() or not deleted_paths:
        return 0
    try:
        dom = parse_xml(content_types)
    except Exception:
        return 0

    deleted_part_names = {f"/{path}" for path in deleted_paths}
    removed = 0
    for override in list(elements_by_local_name(dom, "Override")):
        if override.getAttribute("PartName") in deleted_part_names:
            override.parentNode.removeChild(override)
            removed += 1
    if removed:
        content_types.write_text(dom.toxml(encoding="utf-8").decode("utf-8"), encoding="utf-8")
    return removed


def ensure_content_type_override(unpacked_dir, part_name, content_type):
    content_types = unpacked_dir / "[Content_Types].xml"
    if not content_types.exists():
        return False
    dom = parse_xml(content_types)
    normalized_part = part_name if part_name.startswith("/") else f"/{part_name}"
    for override in elements_by_local_name(dom, "Override"):
        if override.getAttribute("PartName") == normalized_part:
            if override.getAttribute("ContentType") != content_type:
                override.setAttribute("ContentType", content_type)
                write_dom(content_types, dom)
            return False
    override = dom.createElement("Override")
    override.setAttribute("PartName", normalized_part)
    override.setAttribute("ContentType", content_type)
    dom.documentElement.appendChild(override)
    write_dom(content_types, dom)
    return True


def next_number_for_parts(directory, prefix):
    highest = 0
    if directory.exists():
        for file_path in directory.glob(f"{prefix}*.xml"):
            match = re.fullmatch(rf"{re.escape(prefix)}(\d+)\.xml", file_path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def next_slide_id(unpacked_dir):
    slides = get_slide_order(unpacked_dir)
    used = set()
    for slide in slides:
        try:
            used.add(int(slide.get("slide_id") or 0))
        except ValueError:
            continue
    candidate = 256
    while candidate in used:
        candidate += 1
    if candidate > 2147483647:
        raise ValueError("No valid unused slide IDs remain")
    return candidate


def add_slide_to_presentation(unpacked_dir, rel_id, slide_id, position=None):
    pres_path = unpacked_dir / "ppt" / "presentation.xml"
    dom = parse_xml(pres_path)
    slide_lists = elements_by_local_name(dom, "sldIdLst")
    if slide_lists:
        slide_list = slide_lists[0]
    else:
        slide_list = dom.createElement("p:sldIdLst")
        dom.documentElement.appendChild(slide_list)

    new_slide = dom.createElement("p:sldId")
    new_slide.setAttribute("id", str(slide_id))
    new_slide.setAttributeNS(OFFICE_REL_NS, "r:id", rel_id)

    slide_entries = [
        node for node in slide_list.childNodes
        if node.nodeType == node.ELEMENT_NODE and getattr(node, "localName", None) == "sldId"
    ]
    if position is not None and 1 <= position <= len(slide_entries):
        slide_list.insertBefore(new_slide, slide_entries[position - 1])
    else:
        slide_list.appendChild(new_slide)

    write_dom(pres_path, dom)


def pretty_print_xml_file(xml_file):
    try:
        dom = parse_xml(xml_file)
        xml_file.write_text(dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8"), encoding="utf-8")
        return True
    except Exception:
        return False


def condense_xml_file(xml_file):
    try:
        dom = parse_xml(xml_file)
        write_dom(xml_file, dom)
        return True
    except Exception:
        return False


def format_xml_tree(root, pretty=False):
    changed = 0
    for xml_file in list(root.rglob("*.xml")) + list(root.rglob("*.rels")):
        ok = pretty_print_xml_file(xml_file) if pretty else condense_xml_file(xml_file)
        changed += 1 if ok else 0
    return changed


def remove_unreferenced_slide_relationships(unpacked_dir, active_relationship_ids):
    rels_path = unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"
    if not rels_path.exists():
        return 0

    try:
        dom = parse_xml(rels_path)
    except Exception:
        return 0

    removed = 0
    for rel in list(elements_by_local_name(dom, "Relationship")):
        rel_type = rel.getAttribute("Type")
        rel_id = rel.getAttribute("Id")
        if rel_type.endswith("/slide") and rel_id not in active_relationship_ids:
            rel.parentNode.removeChild(rel)
            removed += 1

    if removed:
        rels_path.write_text(dom.toxml(encoding="utf-8").decode("utf-8"), encoding="utf-8")
    return removed


def command_clean(args):
    unpacked_dir = Path(args.unpacked_dir)
    if not unpacked_dir.is_dir():
        print_json({"ok": False, "error": f"Directory not found: {unpacked_dir}"})
        return 1

    slides = get_slide_order(unpacked_dir)
    referenced_slides = {slide["path"] for slide in slides if slide.get("path")}
    active_relationship_ids = {
        slide["relationship_id"] for slide in slides if slide.get("relationship_id")
    }
    deleted = []

    presentation_relationships_removed = remove_unreferenced_slide_relationships(
        unpacked_dir, active_relationship_ids
    )

    slides_dir = unpacked_dir / "ppt" / "slides"
    if slides_dir.exists():
        for slide_file in slides_dir.glob("slide*.xml"):
            relative = slide_file.relative_to(unpacked_dir).as_posix()
            if relative not in referenced_slides:
                slide_file.unlink()
                deleted.append(relative)
                rels_file = rels_path_for_part(unpacked_dir, relative)
                if rels_file.exists():
                    rels_file.unlink()
                    deleted.append(rels_file.relative_to(unpacked_dir).as_posix())

    referenced_targets = collect_relationship_targets(unpacked_dir)

    notes_dir = unpacked_dir / "ppt" / "notesSlides"
    if notes_dir.exists():
        for notes_file in notes_dir.glob("notesSlide*.xml"):
            relative = notes_file.relative_to(unpacked_dir).as_posix()
            if relative not in referenced_targets:
                notes_file.unlink()
                deleted.append(relative)
                rels_file = rels_path_for_part(unpacked_dir, relative)
                if rels_file.exists():
                    rels_file.unlink()
                    deleted.append(rels_file.relative_to(unpacked_dir).as_posix())

    media_dir = unpacked_dir / "ppt" / "media"
    if media_dir.exists():
        referenced_targets = collect_relationship_targets(unpacked_dir)
        for media_file in media_dir.iterdir():
            if not media_file.is_file():
                continue
            relative = media_file.relative_to(unpacked_dir).as_posix()
            if relative not in referenced_targets:
                media_file.unlink()
                deleted.append(relative)

    content_type_overrides_removed = remove_content_type_overrides(unpacked_dir, deleted)
    print_json(
        {
            "ok": True,
            "deleted": deleted,
            "presentation_relationships_removed": presentation_relationships_removed,
            "content_type_overrides_removed": content_type_overrides_removed,
        }
    )
    return 0


def resolve_slide_source(unpacked_dir, source):
    source_path = Path(source)
    candidates = []
    if source_path.is_absolute():
        candidates.append(source_path)
    else:
        candidates.extend(
            [
                unpacked_dir / source,
                unpacked_dir / "ppt" / "slides" / source,
                unpacked_dir / "ppt" / "slideLayouts" / source,
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def create_empty_slide_xml():
    return """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id=\"1\" name=\"\"/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x=\"0\" y=\"0\"/>
          <a:ext cx=\"0\" cy=\"0\"/>
          <a:chOff x=\"0\" y=\"0\"/>
          <a:chExt cx=\"0\" cy=\"0\"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def copy_notes_for_duplicated_slide(unpacked_dir, dest_slide_name, dest_slide_rels_path):
    if not dest_slide_rels_path.exists():
        return []
    dom = parse_xml(dest_slide_rels_path)
    copied = []
    for rel in elements_by_local_name(dom, "Relationship"):
        if not rel.getAttribute("Type").endswith(NOTES_REL_SUFFIX):
            continue
        target = rel.getAttribute("Target")
        source_notes_part = resolve_part_target(f"ppt/slides/{dest_slide_name}", target)
        source_notes_path = unpacked_dir / source_notes_part
        if not source_notes_path.exists():
            continue
        next_notes = next_number_for_parts(unpacked_dir / "ppt" / "notesSlides", "notesSlide")
        dest_notes_name = f"notesSlide{next_notes}.xml"
        dest_notes_part = f"ppt/notesSlides/{dest_notes_name}"
        dest_notes_path = unpacked_dir / dest_notes_part
        dest_notes_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_notes_path, dest_notes_path)
        ensure_content_type_override(unpacked_dir, dest_notes_part, CONTENT_TYPES["notes_slide"])

        source_notes_rels = rels_path_for_part(unpacked_dir, source_notes_part)
        dest_notes_rels = rels_path_for_part(unpacked_dir, dest_notes_part)
        if source_notes_rels.exists():
            dest_notes_rels.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_notes_rels, dest_notes_rels)
            notes_dom = parse_xml(dest_notes_rels)
            for notes_rel in elements_by_local_name(notes_dom, "Relationship"):
                if notes_rel.getAttribute("Type").endswith(SLIDE_REL_SUFFIX):
                    notes_rel.setAttribute("Target", f"../slides/{dest_slide_name}")
            write_dom(dest_notes_rels, notes_dom)

        rel.setAttribute("Target", f"../notesSlides/{dest_notes_name}")
        copied.append(dest_notes_part)
    if copied:
        write_dom(dest_slide_rels_path, dom)
    return copied


def duplicate_slide(unpacked_dir, source_path, position=None, insert=True):
    slides_dir = unpacked_dir / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"
    next_slide = next_number_for_parts(slides_dir, "slide")
    dest_name = f"slide{next_slide}.xml"
    dest_part = f"ppt/slides/{dest_name}"
    dest_path = slides_dir / dest_name
    source_part = source_path.relative_to(unpacked_dir).as_posix()

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)
    source_rels = rels_path_for_part(unpacked_dir, source_part)
    dest_rels = rels_dir / f"{dest_name}.rels"
    if source_rels.exists():
        dest_rels.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_rels, dest_rels)
    else:
        dest_rels.parent.mkdir(parents=True, exist_ok=True)
        write_dom(dest_rels, new_relationships_dom())

    notes = copy_notes_for_duplicated_slide(unpacked_dir, dest_name, dest_rels)
    ensure_content_type_override(unpacked_dir, dest_part, CONTENT_TYPES["slide"])
    pres_rels = unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"
    rel_id = add_relationship(pres_rels, REL_TYPES["slide"], f"slides/{dest_name}")
    slide_id = next_slide_id(unpacked_dir)
    if insert:
        add_slide_to_presentation(unpacked_dir, rel_id, slide_id, position)

    return {
        "created": dest_part,
        "source": source_part,
        "relationship_id": rel_id,
        "slide_id": slide_id,
        "notes_copied": notes,
        "inserted": insert,
    }


def create_slide_from_layout(unpacked_dir, layout_path, position=None, insert=True):
    slides_dir = unpacked_dir / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"
    next_slide = next_number_for_parts(slides_dir, "slide")
    dest_name = f"slide{next_slide}.xml"
    dest_part = f"ppt/slides/{dest_name}"
    dest_path = slides_dir / dest_name
    layout_part = layout_path.relative_to(unpacked_dir).as_posix()

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(create_empty_slide_xml(), encoding="utf-8")
    ensure_content_type_override(unpacked_dir, dest_part, CONTENT_TYPES["slide"])

    dest_rels = rels_dir / f"{dest_name}.rels"
    dest_rels.parent.mkdir(parents=True, exist_ok=True)
    write_dom(dest_rels, new_relationships_dom())
    add_relationship(dest_rels, REL_TYPES["slide_layout"], f"../slideLayouts/{layout_path.name}")

    pres_rels = unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"
    rel_id = add_relationship(pres_rels, REL_TYPES["slide"], f"slides/{dest_name}")
    slide_id = next_slide_id(unpacked_dir)
    if insert:
        add_slide_to_presentation(unpacked_dir, rel_id, slide_id, position)

    return {
        "created": dest_part,
        "source": layout_part,
        "relationship_id": rel_id,
        "slide_id": slide_id,
        "inserted": insert,
    }


def command_add_slide(args):
    unpacked_dir = Path(args.unpacked_dir)
    if not unpacked_dir.is_dir():
        print_json({"ok": False, "error": f"Directory not found: {unpacked_dir}"})
        return 1
    source_path = resolve_slide_source(unpacked_dir, args.source)
    if source_path is None:
        print_json({"ok": False, "error": f"Source slide or layout not found: {args.source}"})
        return 1

    source_relative = source_path.relative_to(unpacked_dir).as_posix()
    if source_relative.startswith("ppt/slideLayouts/"):
        result = create_slide_from_layout(unpacked_dir, source_path, args.position, not args.no_insert)
    elif source_relative.startswith("ppt/slides/"):
        result = duplicate_slide(unpacked_dir, source_path, args.position, not args.no_insert)
    else:
        print_json({"ok": False, "error": f"Source must be under ppt/slides or ppt/slideLayouts: {source_relative}"})
        return 1

    print_json({"ok": True, **result})
    return 0


def missing_relationship_targets(unpacked_dir):
    missing = []
    for rels_file in unpacked_dir.rglob("*.rels"):
        rels_relative = rels_file.relative_to(unpacked_dir).as_posix()
        if "/_rels/" not in rels_relative and rels_relative != "_rels/.rels":
            continue

        if rels_relative == "_rels/.rels":
            source_part = ""
        else:
            source_dir, rels_name = rels_relative.split("/_rels/", 1)
            source_part = f"{source_dir}/{rels_name[:-5]}"

        try:
            rels = relationship_map(rels_file)
        except Exception:
            continue

        for rel in rels.values():
            target = rel.get("target", "")
            if not target or rel.get("target_mode") == "External":
                continue
            if target.startswith("http://") or target.startswith("https://"):
                continue
            resolved = resolve_part_target(source_part, target)
            if resolved and not (unpacked_dir / resolved).exists():
                missing.append(
                    {
                        "relationship_file": rels_relative,
                        "relationship_id": rel.get("id"),
                        "target": target,
                        "resolved": resolved,
                    }
                )
    return missing


def declared_content_types(unpacked_dir):
    content_types = unpacked_dir / "[Content_Types].xml"
    overrides = {}
    defaults = {}
    if not content_types.exists():
        return defaults, overrides
    dom = parse_xml(content_types)
    for default in elements_by_local_name(dom, "Default"):
        extension = default.getAttribute("Extension").lower()
        defaults[extension] = default.getAttribute("ContentType")
    for override in elements_by_local_name(dom, "Override"):
        part_name = override.getAttribute("PartName").lstrip("/")
        overrides[part_name] = override.getAttribute("ContentType")
    return defaults, overrides


def expected_content_type(part_name):
    if part_name == "ppt/presentation.xml":
        return CONTENT_TYPES["presentation"]
    if re.fullmatch(r"ppt/slides/slide\d+\.xml", part_name):
        return CONTENT_TYPES["slide"]
    if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", part_name):
        return CONTENT_TYPES["slide_layout"]
    if re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", part_name):
        return CONTENT_TYPES["slide_master"]
    if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", part_name):
        return CONTENT_TYPES["notes_slide"]
    if re.fullmatch(r"ppt/notesMasters/notesMaster\d+\.xml", part_name):
        return CONTENT_TYPES["notes_master"]
    if re.fullmatch(r"ppt/theme/theme\d+\.xml", part_name):
        return CONTENT_TYPES["theme"]
    return None


def validate_content_type_declarations(unpacked_dir):
    errors = []
    defaults, overrides = declared_content_types(unpacked_dir)
    for file_path in unpacked_dir.rglob("*"):
        if not file_path.is_file():
            continue
        part_name = file_path.relative_to(unpacked_dir).as_posix()
        expected = expected_content_type(part_name)
        if expected and overrides.get(part_name) != expected:
            errors.append(f"Missing or incorrect content type override for {part_name}")
        if part_name.startswith("ppt/media/"):
            extension = file_path.suffix.lower().lstrip(".")
            expected_media = MEDIA_CONTENT_TYPES.get(extension)
            if expected_media and defaults.get(extension) != expected_media and part_name not in overrides:
                errors.append(f"Missing media content type declaration for {part_name}")
    return errors


def validate_relationship_ids(unpacked_dir):
    errors = []
    for rels_file in unpacked_dir.rglob("*.rels"):
        try:
            dom = parse_xml(rels_file)
        except Exception:
            continue
        seen = set()
        duplicates = []
        for rel in elements_by_local_name(dom, "Relationship"):
            rel_id = rel.getAttribute("Id")
            if rel_id in seen:
                duplicates.append(rel_id)
            seen.add(rel_id)
        if duplicates:
            errors.append(
                f"Duplicate relationship IDs in {rels_file.relative_to(unpacked_dir).as_posix()}: {', '.join(sorted(set(duplicates)))}"
            )
    return errors


def validate_slide_ids(unpacked_dir):
    errors = []
    seen = {}
    for slide in get_slide_order(unpacked_dir):
        slide_id = slide.get("slide_id")
        try:
            numeric_id = int(slide_id)
        except (TypeError, ValueError):
            errors.append(f"Invalid non-numeric slide ID: {slide_id}")
            continue
        if numeric_id < 256 or numeric_id > 2147483647:
            errors.append(f"Slide ID out of allowed range 256..2147483647: {numeric_id}")
        if numeric_id in seen:
            errors.append(f"Duplicate slide ID {numeric_id} on slides {seen[numeric_id]} and {slide.get('index')}")
        seen[numeric_id] = slide.get("index")
    return errors


def relationship_refs_in_part(xml_file):
    refs = set()
    try:
        dom = parse_xml(xml_file)
    except Exception:
        return refs
    for node in dom.getElementsByTagName("*"):
        if not node.attributes:
            continue
        for index in range(node.attributes.length):
            attr = node.attributes.item(index)
            if attr.namespaceURI == OFFICE_REL_NS or attr.name in {"r:id", "r:embed", "r:link"}:
                if attr.value:
                    refs.add(attr.value)
    return refs


def validate_relationship_references(unpacked_dir):
    errors = []
    for xml_file in unpacked_dir.rglob("*.xml"):
        part_name = xml_file.relative_to(unpacked_dir).as_posix()
        if part_name == "[Content_Types].xml" or part_name.startswith("docProps/"):
            continue
        refs = relationship_refs_in_part(xml_file)
        if not refs:
            continue
        rels_path = rels_path_for_part(unpacked_dir, part_name)
        rels = relationship_map(rels_path) if rels_path.exists() else {}
        for rel_id in sorted(refs):
            if rel_id not in rels:
                errors.append(f"Missing relationship {rel_id} referenced by {part_name}")
    return errors


def validate_unique_shape_ids(unpacked_dir):
    errors = []
    for slide_file in (unpacked_dir / "ppt" / "slides").glob("slide*.xml") if (unpacked_dir / "ppt" / "slides").exists() else []:
        try:
            dom = parse_xml(slide_file)
        except Exception:
            continue
        ids = []
        for node in elements_by_local_name(dom, "cNvPr"):
            value = node.getAttribute("id")
            if value:
                ids.append(value)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            errors.append(f"Duplicate shape IDs in {slide_file.relative_to(unpacked_dir).as_posix()}: {', '.join(duplicates)}")
    return errors


def validate_slide_layout_ids(unpacked_dir):
    errors = []
    masters_dir = unpacked_dir / "ppt" / "slideMasters"
    if not masters_dir.exists():
        return errors
    for master_file in masters_dir.glob("slideMaster*.xml"):
        master_part = master_file.relative_to(unpacked_dir).as_posix()
        rels_path = rels_path_for_part(unpacked_dir, master_part)
        rels = relationship_map(rels_path) if rels_path.exists() else {}
        try:
            dom = parse_xml(master_file)
        except Exception:
            continue
        for layout_id in elements_by_local_name(dom, "sldLayoutId"):
            rel_id = layout_id.getAttribute("r:id")
            rel = rels.get(rel_id)
            if not rel:
                errors.append(f"Slide master layout relationship {rel_id} is missing in {master_part}")
                continue
            if not rel.get("type", "").endswith(SLIDE_LAYOUT_REL_SUFFIX):
                errors.append(f"Slide master relationship {rel_id} is not a slide layout in {master_part}")
                continue
            target = resolve_part_target(master_part, rel.get("target", ""))
            if not (unpacked_dir / target).exists():
                errors.append(f"Slide layout target does not exist: {master_part} {rel_id} -> {target}")
    return errors


def validate_duplicate_slide_layout_targets(unpacked_dir):
    errors = []
    masters_dir = unpacked_dir / "ppt" / "slideMasters"
    if not masters_dir.exists():
        return errors
    for rels_file in (masters_dir / "_rels").glob("slideMaster*.xml.rels") if (masters_dir / "_rels").exists() else []:
        rels_relative = rels_file.relative_to(unpacked_dir).as_posix()
        source_dir, rels_name = rels_relative.split("/_rels/", 1)
        source_part = f"{source_dir}/{rels_name[:-5]}"
        targets = []
        for rel in relationship_map(rels_file).values():
            if rel.get("type", "").endswith(SLIDE_LAYOUT_REL_SUFFIX):
                targets.append(resolve_part_target(source_part, rel.get("target", "")))
        duplicates = sorted({target for target in targets if targets.count(target) > 1})
        if duplicates:
            errors.append(f"Duplicate slide layout relationships in {rels_relative}: {', '.join(duplicates)}")
    return errors


def validate_notes_slide_references(unpacked_dir):
    warnings = []
    notes_dir = unpacked_dir / "ppt" / "notesSlides"
    if not notes_dir.exists():
        return warnings
    for notes_file in notes_dir.glob("notesSlide*.xml"):
        notes_part = notes_file.relative_to(unpacked_dir).as_posix()
        rels_path = rels_path_for_part(unpacked_dir, notes_part)
        if not rels_path.exists():
            warnings.append(f"Notes slide has no relationship file: {notes_part}")
            continue
        rels = relationship_map(rels_path)
        if not any(rel.get("type", "").endswith(SLIDE_REL_SUFFIX) for rel in rels.values()):
            warnings.append(f"Notes slide has no back-reference to a slide: {notes_part}")
    return warnings


def iter_files_for_zip(input_dir):
    for file_path in sorted(input_dir.rglob("*")):
        if not file_path.is_file():
            continue
        name = file_path.relative_to(input_dir).as_posix()
        if name.startswith("__MACOSX/") or name.endswith(".DS_Store"):
            continue
        yield file_path, name


def command_pack(args):
    input_dir = Path(args.unpacked_dir)
    output_path = Path(args.output_pptx)
    if not input_dir.is_dir():
        print_json({"ok": False, "error": f"Directory not found: {input_dir}"})
        return 1
    if output_path.exists() and not args.overwrite:
        print_json({"ok": False, "error": f"Output file exists: {output_path}"})
        return 1

    original_validation = None
    if args.original:
        original_path = Path(args.original)
        if not original_path.exists():
            print_json({"ok": False, "error": f"Original file not found: {original_path}"})
            return 1
        original_validation = validate_pptx(original_path)

    validation = validate_unpacked(input_dir)
    if validation["errors"] and not args.allow_invalid and not args.skip_validation:
        print_json({"ok": False, "error": "Validation failed", "validation": validation})
        return 1

    package_dir = input_dir
    temp_dir = None
    xml_files_condensed = 0
    if args.condense_xml:
        temp_dir = tempfile.TemporaryDirectory()
        package_dir = Path(temp_dir.name) / "content"
        shutil.copytree(input_dir, package_dir)
        xml_files_condensed = format_xml_tree(package_dir, pretty=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path, name in iter_files_for_zip(package_dir):
            archive.write(file_path, name)

    if temp_dir:
        temp_dir.cleanup()

    packed_validation = validate_pptx(output_path)
    print_json(
        {
            "ok": not packed_validation["errors"],
            "output": str(output_path),
            "validation": packed_validation,
            "pre_pack_validation": validation,
            "original_validation": original_validation,
            "xml_files_condensed": xml_files_condensed,
        }
    )
    return 0 if not packed_validation["errors"] else 1


def validate_unpacked(unpacked_dir):
    errors = []
    warnings = []
    required = [
        "[Content_Types].xml",
        "_rels/.rels",
        "ppt/presentation.xml",
        "ppt/_rels/presentation.xml.rels",
    ]
    for relative in required:
        if not (unpacked_dir / relative).exists():
            errors.append(f"Missing required part: {relative}")

    xml_count = 0
    for xml_file in list(unpacked_dir.rglob("*.xml")) + list(unpacked_dir.rglob("*.rels")):
        xml_count += 1
        try:
            parse_xml(xml_file)
        except ExpatError as exc:
            errors.append(f"Invalid XML in {xml_file.relative_to(unpacked_dir).as_posix()}: {exc}")
        except Exception as exc:
            errors.append(f"Could not parse {xml_file.relative_to(unpacked_dir).as_posix()}: {exc}")

    slides = get_slide_order(unpacked_dir)
    if not slides:
        warnings.append("No slides found in ppt/presentation.xml")
    for slide in slides:
        if slide["path"] and not slide["exists"]:
            errors.append(f"Referenced slide does not exist: {slide['path']}")

    for missing in missing_relationship_targets(unpacked_dir):
        errors.append(
            "Relationship target does not exist: "
            f"{missing['relationship_file']} {missing['relationship_id']} -> {missing['resolved']}"
        )

    errors.extend(validate_relationship_ids(unpacked_dir))
    errors.extend(validate_slide_ids(unpacked_dir))
    errors.extend(validate_relationship_references(unpacked_dir))
    errors.extend(validate_content_type_declarations(unpacked_dir))
    errors.extend(validate_unique_shape_ids(unpacked_dir))
    errors.extend(validate_slide_layout_ids(unpacked_dir))
    errors.extend(validate_duplicate_slide_layout_targets(unpacked_dir))
    warnings.extend(validate_notes_slide_references(unpacked_dir))

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {"xml_files_checked": xml_count, "slides": len(slides)},
    }


def validate_pptx(pptx_path):
    errors = []
    warnings = []
    try:
        with zipfile.ZipFile(pptx_path, "r") as archive:
            corrupt = archive.testzip()
            if corrupt:
                errors.append(f"Corrupt zip member: {corrupt}")
    except zipfile.BadZipFile as exc:
        return {"valid": False, "errors": [f"Bad zip file: {exc}"], "warnings": [], "stats": {}}

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            safe_extract(pptx_path, Path(temp_dir))
            validation = validate_unpacked(Path(temp_dir))
        except Exception as exc:
            return {"valid": False, "errors": [str(exc)], "warnings": warnings, "stats": {}}

    validation["errors"] = errors + validation["errors"]
    validation["warnings"] = warnings + validation["warnings"]
    validation["valid"] = not validation["errors"]
    return validation


def command_validate(args):
    path = Path(args.path)
    if not path.exists():
        print_json({"valid": False, "errors": [f"Path not found: {path}"], "warnings": [], "stats": {}})
        return 1
    validation = validate_unpacked(path) if path.is_dir() else validate_pptx(path)
    print_json(validation)
    return 0 if validation["valid"] else 1


def main():
    parser = argparse.ArgumentParser(description="OOXML helpers for PowerPoint files")
    subparsers = parser.add_subparsers(dest="command", required=True)

    unpack_parser = subparsers.add_parser("unpack", help="Extract a .pptx to a directory")
    unpack_parser.add_argument("pptx")
    unpack_parser.add_argument("output_dir")
    unpack_parser.add_argument("--overwrite", action="store_true")
    unpack_parser.add_argument("--pretty-xml", action="store_true", help="Pretty-print XML after extraction for manual editing")
    unpack_parser.set_defaults(func=command_unpack)

    list_parser = subparsers.add_parser("list", help="List slides in a .pptx or unpacked directory")
    list_parser.add_argument("path")
    list_parser.set_defaults(func=command_list)

    clean_parser = subparsers.add_parser("clean", help="Remove unreferenced slide, notes, and media parts")
    clean_parser.add_argument("unpacked_dir")
    clean_parser.set_defaults(func=command_clean)

    add_slide_parser = subparsers.add_parser("add-slide", help="Duplicate a slide or create a slide from a layout in an unpacked deck")
    add_slide_parser.add_argument("unpacked_dir")
    add_slide_parser.add_argument("source", help="slideN.xml or slideLayoutN.xml, or a relative path under ppt/slides or ppt/slideLayouts")
    add_slide_parser.add_argument("--position", type=int, help="1-based insertion position in the deck; defaults to append")
    add_slide_parser.add_argument("--no-insert", action="store_true", help="Create the part and relationship but do not add it to presentation.xml")
    add_slide_parser.set_defaults(func=command_add_slide)

    pack_parser = subparsers.add_parser("pack", help="Pack an unpacked directory into a .pptx")
    pack_parser.add_argument("unpacked_dir")
    pack_parser.add_argument("output_pptx")
    pack_parser.add_argument("--overwrite", action="store_true")
    pack_parser.add_argument("--allow-invalid", action="store_true")
    pack_parser.add_argument("--original", help="Original .pptx to validate as a baseline before packing")
    pack_parser.add_argument("--skip-validation", action="store_true", help="Pack without blocking on pre-pack validation errors")
    pack_parser.add_argument("--no-condense-xml", dest="condense_xml", action="store_false", help="Do not condense XML in the packaged copy")
    pack_parser.set_defaults(condense_xml=True)
    pack_parser.set_defaults(func=command_pack)

    validate_parser = subparsers.add_parser("validate", help="Validate .pptx structure or unpacked directory")
    validate_parser.add_argument("path")
    validate_parser.set_defaults(func=command_validate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
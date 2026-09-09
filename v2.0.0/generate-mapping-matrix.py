#!/usr/bin/env python3
"""Generate a self-contained HTML Crosswalk matrix for the QUADRIGA schema.

The matrix is organised around the *entities* of the application profile
(``OpenEducationalResource``, ``Author``, ``Contributor``, ``UsedTool``,
``Chapter``, ``LearningObjective``, ``SupplementalMaterial``, …).  Every
entity gets its own section; the entity's properties are listed directly
below it.

Entities are no longer expanded as a tree.  When a property references
another entity, the matrix only prints a small reference link that points to
that entity's section further down in the list.  Reusable *value types*
(e.g. ``MultilingualText``, ``orcid``, ``license``) are not entities; their
``x-mappings`` are inlined into the referencing property row instead.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

#: The root schema file, displayed as ``OpenEducationalResource``.
ROOT_SCHEMA = "schema.json"

#: Display-name overrides.  Every other entity uses its JSON file stem.
ENTITY_DISPLAY_NAMES = {
    "schema.json": "OpenEducationalResource",
}

#: Preferred left-to-right order of the external vocabulary columns.
COLUMN_ORDER = ["dc", "dcterms", "schema", "modalia", "hermes", "lrmi", "dcat"]

#: Recursion guard for deriving value ranges from nested schemas.
MAX_VALUE_RANGE_DEPTH = 4

#: Human-readable labels for reusable value types and scalar string formats.
VALUE_LABELS = {
    "string": "Text",
    "MultilingualText": "Multilingual Text",
    "timeRequired": "ISO 8601 duration",
    "duration": "ISO 8601 duration",
    "date": "ISO 8601 date",
    "uri": "URI",
    "language": "ISO 639-1 language code",
    "SemVer": "SemVer",
    "license": "license URI",
    "orcid": "ORCID",
}

#: Value-range labels that link to their external specification.
VALUE_LINKS = {
    "SemVer": "https://semver.org",
}


@dataclass
class EntityRef:
    """A reference from a property to another entity of the profile."""

    filename: str
    label: str
    description: str = ""


@dataclass
class Row:
    """A single row of the crosswalk matrix."""

    name: str
    filename: str
    xm: dict | None
    depth: int = 0
    is_entity: bool = False
    cardinality: str = ""
    value_range: str = ""
    description: str = ""
    refs: list[EntityRef] = field(default_factory=list)


class SchemaRepository:
    """Load and cache the JSON schema files of one schema version."""

    def __init__(self, version_dir: str | Path) -> None:
        self.version = Path(version_dir)
        self._cache: dict[str, dict] = {}

    def exists(self, filename: str) -> bool:
        """Return True if the given schema file exists in the version directory."""
        return (self.version / filename).is_file()

    def get(self, filename: str) -> dict:
        """Return the parsed JSON of a schema file, loading and caching it once."""
        if filename not in self._cache:
            with (self.version / filename).open(encoding="utf-8") as fh:
                self._cache[filename] = json.load(fh)
        return self._cache[filename]

    def is_entity(self, filename: str) -> bool:
        """Return True for the root schema or any schema whose root is an object."""
        if not self.exists(filename):
            return False
        if filename == ROOT_SCHEMA:
            return True
        return self.get(filename).get("type") == "object"

    @staticmethod
    def display_name(filename: str) -> str:
        """Return the display name of an entity file."""
        return ENTITY_DISPLAY_NAMES.get(filename, Path(filename).stem)

    @staticmethod
    def iter_refs(node: object) -> list[str]:
        """Recursively collect every ``$ref`` value inside a schema node."""
        refs: list[str] = []
        if isinstance(node, dict):
            if "$ref" in node:
                refs.append(node["$ref"])
            for value in node.values():
                refs.extend(SchemaRepository.iter_refs(value))
        elif isinstance(node, list):
            for item in node:
                refs.extend(SchemaRepository.iter_refs(item))
        return refs


def element_display_name(name: str) -> str:
    """Strip the transport-only ``LIST`` suffix from a property name.

    JSON Schema forbids two declarations of the same key, which is why a list
    element and its item element are split (``keywordLIST`` / ``keyword``).  The
    matrix shows them as the single logical element ``keyword`` instead.
    """
    if name.endswith("LIST") and len(name) > len("LIST"):
        return name[: -len("LIST")]
    return name


def array_subschema(schema: dict) -> dict | None:
    """Return the array-like part of a schema (following ``oneOf``/``anyOf``)."""
    if schema.get("type") == "array" or "items" in schema:
        return schema
    for key in ("oneOf", "anyOf"):
        branches = schema.get(key)
        if isinstance(branches, list):
            for branch in branches:
                if isinstance(branch, dict) and (
                    branch.get("type") == "array" or "items" in branch
                ):
                    return branch
    return None


def derive_cardinality(schema: dict, ref_schema: dict, *, required: bool) -> str:
    """Derive a UML-style cardinality hint from the native schema keywords.

    The lower bound comes from the parent object's ``required`` list, the upper
    bound and repetition from the property's ``minItems`` / ``maxItems``.  A pure
    ``$ref`` is resolved so array-valued reusable types (e.g. ``credit``) are
    detected as well.  ``n`` denotes an unbounded maximum.
    """
    effective = schema if array_subschema(schema) is not None else ref_schema
    array_schema = array_subschema(effective)
    if array_schema is None:
        return "1" if required else "0..1"

    min_items = array_schema.get("minItems")
    minimum = min_items if required and isinstance(min_items, int) and min_items > 0 else 0
    maximum = array_schema.get("maxItems")
    if not isinstance(maximum, int):
        maximum = None

    if maximum is not None and minimum == maximum:
        return str(minimum)
    return f"{minimum}..{'n' if maximum is None else maximum}"


def value_range(schema: dict, repo: SchemaRepository, *, depth: int = 0) -> str:
    """Return a human-readable value range for a schema node.

    Enumerations are expanded to a semicolon-separated list of quoted values;
    references show the referenced type name.  Array multiplicity is conveyed by
    the cardinality column, so no ``[]`` suffix is added.
    """
    if depth > MAX_VALUE_RANGE_DEPTH or not isinstance(schema, dict):
        return ""

    ref = schema.get("$ref")
    if ref and repo.exists(ref):
        ref_data = repo.get(ref)
        if array_subschema(ref_data) is not None:
            return value_range(ref_data, repo, depth=depth + 1)
        stem = Path(ref).stem
        return VALUE_LABELS.get(stem, stem)

    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return _enum_range(enum)

    array_schema = array_subschema(schema)
    if array_schema is not None:
        return _array_value_range(array_schema, repo, depth)

    return _composite_value_range(schema, repo, depth)


def _enum_range(enum: list) -> str:
    """Expand enum values into a semicolon-separated list of quoted strings."""
    return "; ".join(f'"{value}"' for value in enum)


def _array_value_range(array_schema: dict, repo: SchemaRepository, depth: int) -> str:
    """Value range of an array element (multiplicity is shown as cardinality)."""
    items = array_schema.get("items", {})
    if isinstance(items, dict) and items.get("enum"):
        return _enum_range(items["enum"])
    return value_range(items, repo, depth=depth + 1) or "array"


def _composite_value_range(schema: dict, repo: SchemaRepository, depth: int) -> str:
    """Value range of a ``oneOf``/``anyOf`` union or a plain scalar schema."""
    for key in ("oneOf", "anyOf"):
        branches = schema.get(key)
        if isinstance(branches, list):
            parts: list[str] = []
            for branch in branches:
                branch_range = value_range(branch, repo, depth=depth + 1)
                if branch_range and branch_range not in parts:
                    parts.append(branch_range)
            if parts:
                return " | ".join(parts)
    return _scalar_value_range(schema)


def _scalar_value_range(schema: dict) -> str:
    """Value range of a non-array, non-union schema node."""
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(VALUE_LABELS.get(str(item), str(item)) for item in schema_type)
    if schema_type == "object":
        return ""
    if schema_type == "string":
        fmt = schema.get("format")
        if isinstance(fmt, str) and fmt:
            return VALUE_LABELS.get(fmt, fmt)
        return VALUE_LABELS.get("string", "string")
    if isinstance(schema_type, str) and schema_type:
        return schema_type
    return ""


def discover_entities(repo: SchemaRepository) -> list[str]:
    """Return all entity files reachable from the root, in breadth-first order."""
    order: list[str] = []
    seen: set[str] = set()
    queue: list[str] = [ROOT_SCHEMA]

    while queue:
        filename = queue.pop(0)
        if filename in seen or not repo.is_entity(filename):
            continue
        seen.add(filename)
        order.append(filename)
        for prop in repo.get(filename).get("properties", {}).values():
            queue.extend(
                ref
                for ref in SchemaRepository.iter_refs(prop)
                if ref not in seen and repo.is_entity(ref)
            )

    # Include entity files that are not reachable from the root.
    order.extend(
        path.name
        for path in sorted(repo.version.glob("*.json"))
        if path.name not in seen and repo.is_entity(path.name)
    )

    return order


def build_rows(repo: SchemaRepository) -> tuple[list[Row], set[str]]:
    """Build the flat list of matrix rows and the set of mapped vocabularies."""
    rows: list[Row] = []
    mapped_schemas: set[str] = set()

    def collect(xm: dict | None) -> None:
        if isinstance(xm, dict):
            for key in xm:
                if not key.startswith("$"):
                    mapped_schemas.add(key)

    def add_property(
        name: str,
        schema: object,
        filename: str,
        depth: int,
        *,
        required: bool = False,
    ) -> None:
        if not isinstance(schema, dict):
            return

        referenced = schema.get("$ref")
        ref_schema = repo.get(referenced) if referenced and repo.exists(referenced) else {}

        cardinality = derive_cardinality(schema, ref_schema, required=required)
        value_text = value_range(schema, repo)

        # A list element and its item element are only split because JSON Schema
        # forbids duplicate keys.  The matrix always shows the *item's* mapping
        # (inline or referenced) under the property's non-list name, e.g.
        # ``author`` for ``authorLIST``; list-level mappings are not displayed.
        items = schema.get("items")
        item_ref = items.get("$ref") if isinstance(items, dict) else None
        item_schema = (
            repo.get(item_ref) if isinstance(item_ref, str) and repo.exists(item_ref) else {}
        )

        if isinstance(items, dict):
            xm = items.get("x-mappings")
            if xm is None:
                xm = item_schema.get("x-mappings")
        else:
            xm = schema.get("x-mappings")
            if xm is None:
                # A pure reference to a reusable value type: inherit its mappings.
                xm = ref_schema.get("x-mappings")
        collect(xm)

        refs: list[EntityRef] = []
        for ref in SchemaRepository.iter_refs(schema):
            if repo.is_entity(ref) and all(r.filename != ref for r in refs):
                refs.append(
                    EntityRef(
                        filename=ref,
                        label=repo.display_name(ref),
                        description=repo.get(ref).get("description", ""),
                    )
                )

        # Lists show the item's definition (description) under the property's
        # non-list name; list-level descriptions are only a fallback.
        if isinstance(items, dict):
            description = items.get("description") or item_schema.get("description", "")
            if not description:
                description = schema.get("description") or ""
        else:
            description = schema.get("description") or ref_schema.get("description", "")

        rows.append(
            Row(
                name=element_display_name(name),
                filename=filename,
                xm=xm,
                depth=depth,
                cardinality=cardinality,
                value_range=value_text,
                description=description,
                refs=refs,
            )
        )

        # Inline anonymous objects keep their properties as indented sub-rows.
        if schema.get("type") == "object" and isinstance(schema.get("properties"), dict):
            sub_required = set(schema.get("required", []))
            for sub_name, sub_schema in schema["properties"].items():
                add_property(
                    sub_name,
                    sub_schema,
                    filename,
                    depth + 1,
                    required=sub_name in sub_required,
                )

    for filename in discover_entities(repo):
        data = repo.get(filename)
        xm = data.get("x-mappings")
        collect(xm)
        rows.append(
            Row(
                name=repo.display_name(filename),
                filename=filename,
                xm=xm,
                is_entity=True,
                description=data.get("description", ""),
            )
        )
        required = set(data.get("required", []))
        for prop_name, prop_schema in data.get("properties", {}).items():
            add_property(
                prop_name,
                prop_schema,
                filename,
                depth=0,
                required=prop_name in required,
            )

    return rows, mapped_schemas


def ordered_columns(mapped_schemas: set[str]) -> list[str]:
    """Column order: the known vocabularies first, then any extras sorted."""
    ordered = [c for c in COLUMN_ORDER if c in mapped_schemas]
    ordered += sorted(c for c in mapped_schemas if c not in COLUMN_ORDER)
    return ordered


def html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def resolve_uri(target: str, context: dict) -> str:
    """Resolve a prefixed target (e.g. ``dc:title``) to a full URI."""
    if not target:
        return ""
    if target.startswith(("http://", "https://")):
        return target
    if ":" in target:
        prefix, local = target.split(":", 1)
        base = context.get(prefix, "")
        return f"{base}{local}"
    return ""


def tooltip_icon(*texts: str) -> str:
    """Return an info icon with the given texts as tooltip, if any text exists."""
    comment = "\n\n".join(t for t in texts if t)
    if not comment:
        return ""
    return f' <span class="tip" data-tip="{html_escape(comment)}">ⓘ</span>'


def format_sub_cell(entry: dict, context: dict) -> str:
    """Format a single mapping entry as a sub-cell div."""
    relation = entry.get("relation", "")
    target = entry.get("target", "")
    comment = entry.get("$comment", "")
    short_rel = relation.replace("skos:", "") if relation else ""
    css_class = short_rel.lower() if short_rel else "unknown"

    if target:
        uri = resolve_uri(target, context)
        if uri:
            target_html = (
                f'<a class="target" href="{html_escape(uri)}" target="_blank">'
                f"{html_escape(target)}</a>"
            )
        else:
            target_html = f'<span class="target">{html_escape(target)}</span>'
        content = (
            f'<span class="label-box"><span class="relation">{short_rel}</span>'
            f'<span class="target-line">{target_html}{tooltip_icon(comment)}</span></span>'
        )
    else:
        content = (
            f'<span class="label-box"><span class="relation">{short_rel}</span>'
            f"{tooltip_icon(comment)}</span>"
        )

    return f'<div class="sub-cell {css_class}">{content}</div>'


def cell_content(xm: dict | None, schema_name: str, context: dict) -> tuple[str, str]:
    """Return ``(html_content, td_css_class)`` for one vocabulary column."""
    if xm is None:
        return "", ""

    entry = xm.get(schema_name)
    if entry is None:
        return "k. A.", "na"

    entries = entry if isinstance(entry, list) else [entry]
    sub_cells = [format_sub_cell(e, context) for e in entries]

    if len(entries) == 1:
        relation = entries[0].get("relation", "")
        td_css = relation.replace("skos:", "").lower() if relation else "unknown"
        return "".join(sub_cells), td_css

    return f'<div class="cell-stack">{"".join(sub_cells)}</div>', "multi"


def indent_guides(rows: list[Row], idx: int, indent_step: int = 18) -> str:
    """Return tree-style guide lines for an indented (nested) property row."""
    depth = rows[idx].depth
    if depth <= 0:
        return ""

    half = indent_step // 2
    guides = []
    # Vertical lines for ancestor levels (relevant when nesting exceeds one level).
    for level in range(1, depth):
        left = level * indent_step - half
        guides.append(f'<span class="guide-vline" style="left: {left}px"></span>')

    # Connector at the row's own level: an elbow for the last child of a group,
    # a vertical line with a tick for the ones in between.
    is_last = True
    for following in rows[idx + 1 :]:
        if following.depth < depth:
            break
        if following.depth == depth:
            is_last = False
            break
    cls = "guide-last" if is_last else "guide-mid"
    left = depth * indent_step - half
    guides.append(f'<span class="{cls}" style="left: {left}px"></span>')
    return "".join(guides)


def name_cell(row: Row, guides: str = "", base_url: str = "", indent_step: int = 18) -> str:
    """Render the sticky first column of a row.

    ``base_url`` turns the schema-file links into absolute URLs of the deployed
    application profile (derived from the schema ``$id``), so the matrix works on
    GitHub Pages as well as from a local build.
    """
    href = html_escape(base_url + row.filename if base_url else row.filename)
    if row.is_entity:
        link = (
            f'<a class="entity-link" href="{href}" target="_blank">'
            f"{html_escape(row.name)}</a>"
        )
        badge = '<span class="entity-badge">Entität</span>'
        return f"{link}{badge}{tooltip_icon(general_comment(row.xm))}"

    link = (
        f'<a class="element-link" href="{href}" target="_blank">'
        f"{html_escape(row.name)}</a>"
    )
    style = f' style="padding-left: {row.depth * indent_step}px"' if row.depth else ""
    inner = f"{guides}{link}{tooltip_icon(general_comment(row.xm))}"
    return f'<td class="element-name" data-cell="name"{style}>{inner}</td>'


def entity_link(ref: EntityRef) -> str:
    """Render a reference to an entity section further down the list."""
    return (
        f'<a class="entity-ref" href="#entity-{html_escape(ref.label)}"'
        f' title="Entität: {html_escape(ref.description)}">{html_escape(ref.label)}</a>'
    )


def value_range_cell(row: Row) -> str:
    """Render the frozen Wertbereich column, including entity references."""
    ref_labels = {ref.label for ref in row.refs}
    parts: list[str] = []
    if row.value_range and row.value_range not in ref_labels:
        parts.append(value_range_html(row.value_range))
    parts.extend(entity_link(ref) for ref in row.refs)
    if not parts:
        return '<td class="value-range"></td>'
    return f'<td class="value-range">{" ".join(parts)}</td>'


def value_range_html(text: str) -> str:
    """Render a value-range label, linking known external specifications."""
    link = VALUE_LINKS.get(text)
    if link:
        return (
            f'<a class="value-link" href="{link}" target="_blank">'
            f"{html_escape(text)}</a>"
        )
    return html_escape(text)


def description_cell(row: Row) -> str:
    """Render the frozen Description column, clipped with ellipsis + tooltip."""
    if not row.description:
        return '<td class="description"></td>'
    return (
        '<td class="description">'
        f'<div class="desc-clip" data-tip="{html_escape(row.description)}">'
        f"{html_escape(row.description)}</div></td>"
    )


def general_comment(xm: dict | None) -> str:
    """Return the top-level ``$comment`` of an ``x-mappings`` block."""
    if xm is None:
        return ""
    comment = xm.get("$comment", "")
    return comment if isinstance(comment, str) else ""


def row_class(row: Row) -> str:
    """CSS class for a matrix row."""
    if row.is_entity:
        return "entity-row"
    return "prop-row"


def anchor_id(row: Row) -> str:
    """Stable anchor for an entity section."""
    return f"entity-{row.name}" if row.is_entity else ""


def generate_html(rows: list[Row], columns: list[str], context: dict, base_url: str = "") -> str:
    """Generate the self-contained HTML document."""
    table_rows: list[str] = []
    ncols = 4 + len(columns)
    for idx, row in enumerate(rows):
        if row.is_entity and table_rows:
            # Visual breathing room between entity sections.
            table_rows.append(f'  <tr class="entity-gap"><td colspan="{ncols}"></td></tr>')

        cells = []
        for col in columns:
            text, css_class = cell_content(row.xm, col, context)
            cells.append(
                f'<td class="vocab {css_class}" data-vocab="{html_escape(col)}">{text}</td>'
            )
        # Cardinality is a property-level concept; entity rows stay empty.
        card = f'<td class="cardinality">{html_escape(row.cardinality)}</td>'
        value = value_range_cell(row)
        desc = description_cell(row)

        if row.is_entity:
            anchor = f' id="{html_escape(anchor_id(row))}"'
            entity_name = name_cell(row, base_url=base_url)
            table_rows.append(
                f'  <tr class="{row_class(row)}"{anchor}>\n'
                f'    <th class="element-name entity-name">{entity_name}</th>\n'
                f"    {card}\n"
                f"    {value}\n"
                f"    {desc}\n"
                f"    {''.join(cells)}\n"
                f"  </tr>"
            )
        else:
            table_rows.append(
                f'  <tr class="{row_class(row)}">\n'
                f"    {name_cell(row, indent_guides(rows, idx), base_url)}\n"
                f"    {card}\n"
                f"    {value}\n"
                f"    {desc}\n"
                f"    {''.join(cells)}\n"
                f"  </tr>"
            )

    col_headers = [
        ('<th class="cardinality-header">Kardinalität</th>'),
        '<th class="value-range-header">Wertebereich</th>',
        '<th class="description-header">Beschreibung</th>',
    ]
    for col in columns:
        uri = context.get(col)
        label = (
            f'<a href="{html_escape(uri)}" target="_blank">{html_escape(col)}</a>'
            if uri
            else html_escape(col)
        )
        col_headers.append(f'<th class="vocab-header" data-vocab="{html_escape(col)}">{label}</th>')

    vocab_filters = "".join(
        '<label class="filter-item">'
        f'<input type="checkbox" data-vocab-filter="{html_escape(col)}" checked>'
        f"<span>{html_escape(col)}</span></label>"
        for col in columns
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QUADRIGA Application Profile: Metadaten Crosswalk Matrix</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 1rem;
    padding-top: var(--header-offset, 0px);
    background: #fafafa;
    text-align: center;
  }}
  a {{ color: inherit; text-decoration: inherit; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.5rem; }}
  /* Let the browser's own scrollbars scroll the table, so the sticky header and
     the frozen left columns stay relative to the viewport. */
  .table-wrap {{ overflow: visible; }}
  .table-wrap table {{ margin: 0 auto; }}
  table {{
    border-collapse: collapse;
    font-size: 0.85rem;
    table-layout: fixed;
    width: 100%;
    min-width: 1970px;
  }}
  th, td {{
    border: 1.5px solid #333;
    padding: 4px 8px;
    text-align: center;
    white-space: nowrap;
    vertical-align: middle;
    box-sizing: border-box;
  }}
  thead th {{
    position: sticky;
    top: var(--header-offset, 0px);
    background: #333;
    color: #fff;
    z-index: 2;
    border-color: #333;
  }}
  /* Fixierte Spalten: Eigenschaft | Kardinalität | Wertebereich | Beschreibung */
  .element-name {{
    position: sticky;
    left: 0;
    width: 250px;
    background: #f0f0f0;
    text-align: left;
    font-weight: 600;
    white-space: normal;
    overflow-wrap: anywhere;
    z-index: 1;
  }}
  td.cardinality,
  td.value-range,
  td.description {{
    position: sticky;
    z-index: 1;
    background: #f7f7f7;
    text-align: left;
  }}
  td.cardinality {{ left: 250px; width: 110px; text-align: center; }}
  td.value-range {{ left: 360px; width: 240px; }}
  td.description {{ left: 600px; width: 250px; }}
  td.description,
  thead th.description-header {{ border-right: 2.5px solid #333; }}
  thead th:first-child {{ z-index: 3; background: #333; }}
  thead th.cardinality-header,
  thead th.value-range-header,
  thead th.description-header {{
    position: sticky;
    top: var(--header-offset, 0px);
    z-index: 3;
  }}
  thead th.cardinality-header {{ left: 250px; width: 110px; }}
  thead th.value-range-header {{ left: 360px; width: 240px; }}
  thead th.description-header {{ left: 600px; width: 250px; }}
  .description .desc-clip {{
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    max-width: 100%;
    overflow: hidden;
    overflow-wrap: anywhere;
    text-overflow: ellipsis;
    white-space: normal;
    font-size: inherit;
    color: #444;
    font-weight: 400;
  }}
  .value-range {{
    font-variant-numeric: tabular-nums;
    color: #333;
    white-space: normal;
    overflow-wrap: anywhere;
  }}
  .value-range .entity-ref:first-child {{ margin-left: 0; }}
  .value-link {{ color: #14385f; text-decoration: underline; }}
  .value-link:hover {{ color: #0a2540; }}
  /* Vocabulary columns may wrap their long target URIs */
  .vocab, .vocab-header {{ white-space: normal; overflow-wrap: anywhere; }}

  /* Entity section header rows */
  .entity-row > * {{ border-top: 2.5px solid #333; }}
  .entity-gap td {{
    border: none;
    padding: 0;
    height: 18px;
    line-height: 0;
    background: transparent;
  }}
  .entity-row .element-name,
  .entity-row td.cardinality,
  .entity-row td.value-range,
  .entity-row td.description {{ background: #dbe7f5; }}
  .entity-row .entity-name {{ font-size: 1rem; text-align: left; }}
  .entity-row {{ scroll-margin-top: 2.6rem; }}
  .entity-link {{ color: #14385f; }}
  .entity-link:hover {{ text-decoration: underline; }}
  .entity-badge {{
    font-size: 0.65rem;
    letter-spacing: 0.02em;
    background: #333;
    color: #fff;
    border-radius: 3px;
    padding: 1px 5px;
    margin-left: 7px;
    vertical-align: middle;
    white-space: nowrap;
  }}

  /* Property rows */
  .prop-row .element-name {{ background: #f7f7f7; }}
  .element-link:hover {{ text-decoration: underline; }}
  /* Derived cardinality column (properties only) */
  .cardinality,
  thead th.cardinality-header {{
    text-align: center;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
    min-width: 46px;
  }}
  .cardinality {{ background: #fbfbfb; }}
  .entity-row .cardinality {{ background: #dbe7f5; }}

  /* Indent guide lines for nested properties / array items */
  .guide-vline,
  .guide-mid {{
    position: absolute;
    top: 0;
    bottom: 0;
    border-left: 1.5px solid #999;
  }}
  .guide-mid::after {{
    content: '';
    position: absolute;
    top: 50%;
    left: 0;
    width: 7px;
    border-top: 1.5px solid #999;
  }}
  .guide-last {{
    position: absolute;
    top: 0;
    height: 50%;
    width: 7px;
    border-left: 1.5px solid #999;
    border-bottom: 1.5px solid #999;
    border-bottom-left-radius: 3px;
  }}

  /* Reference to another entity further down the list */
  .entity-ref {{
    display: inline-block;
    margin-left: 7px;
    font-size: 0.72rem;
    font-weight: 600;
    color: #0b5394;
    background: #dbe9fb;
    border: 1px solid #a9c7ec;
    border-radius: 10px;
    padding: 0 7px;
    text-decoration: none;
    white-space: nowrap;
    vertical-align: middle;
  }}
  .entity-ref:hover {{ background: #c3daf7; }}

  /* relation colors - Okabe-Ito colorblind-safe palette */
  .exactmatch {{ background: #009e73; }}
  .closematch {{ background: #56b4e9; }}
  .narrowmatch {{ background: #e69f00; }}
  .broadmatch {{ background: #f0e442; }}
  .na {{ background: #ddd; }}
  .sub-cell {{
    padding: 3px 6px;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .sub-cell + .sub-cell {{ border-top: 1.5px solid #333; }}
  .multi {{ padding: 0; }}
  .cell-stack {{
    display: flex;
    flex-direction: column;
  }}
  .cell-stack > .sub-cell {{ flex: 1 1 auto; }}
  .label-box {{
    display: inline-block;
    min-width: 0;
    max-width: 100%;
    background: rgba(255,255,255,0.45);
    border-radius: 3px;
    padding: 1px 3px;
  }}
  .relation {{ display: block; font-size: 0.75em; color: inherit; opacity: 0.8; }}
  .target-line {{ display: block; }}
  a.target, a.target:visited {{
    font-weight: 600;
    color: inherit;
    text-decoration: none;
    overflow-wrap: anywhere;
  }}
  a.target:hover {{ text-decoration: underline; }}
  .tip {{ cursor: help; font-size: 0.85em; position: relative; }}
  #tooltip {{
    position: fixed;
    background: #333;
    color: #fff;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 0.82rem;
    max-width: 350px;
    white-space: normal;
    pointer-events: none;
    z-index: 1000;
    display: none;
    line-height: 1.4;
  }}
  .legend {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    justify-content: center;
    margin-bottom: 0.75rem;
    font-size: 0.82rem;
    align-items: center;
  }}
  .legend-item {{ display: inline-flex; align-items: center; gap: 4px; }}
  .legend-swatch {{
    width: 14px;
    height: 14px;
    border: 1px solid #bbb;
    border-radius: 2px;
    display: inline-block;
  }}
  .hint {{ font-size: 0.8rem; color: #555; margin-bottom: 0.75rem; }}
  .page-header {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 5;
    background: #fafafa;
    padding: 0 1rem 0.25rem;
    border-bottom: 1px solid #ccc;
  }}
  .filters {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.75rem;
    font-size: 0.82rem;
  }}
  .filters-label {{ font-weight: 600; }}
  .filter-item {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    border: 1px solid #bbb;
    border-radius: 12px;
    padding: 1px 9px;
    background: #fff;
  }}
  .filter-item input {{ cursor: pointer; margin: 0; }}
  .filter-btn {{
    font: inherit;
    cursor: pointer;
    border: 1px solid #bbb;
    border-radius: 4px;
    background: #f0f0f0;
    padding: 2px 9px;
  }}
  .filter-btn:hover {{ background: #e4e4e4; }}
</style>
</head>
<body>
<div class="page-header" id="page-header">
<h1>QUADRIGA Schema - Mapping-Matrix</h1>
<div class="legend">
  <span style="font-weight:600">SKOS-Relationen:</span>
  <span class="legend-item"><span class="legend-swatch exactmatch"></span>
    <a href="http://www.w3.org/2004/02/skos/core#exactMatch" target="_blank">exactMatch</a></span>
  <span class="legend-item"><span class="legend-swatch broadmatch"></span>
    <a href="http://www.w3.org/2004/02/skos/core#broadMatch" target="_blank">broadMatch</a></span>
  <span class="legend-item"><span class="legend-swatch narrowmatch"></span>
    <a href="http://www.w3.org/2004/02/skos/core#narrowMatch" target="_blank">narrowMatch</a></span>
  <span class="legend-item"><span class="legend-swatch closematch"></span>
    <a href="http://www.w3.org/2004/02/skos/core#closeMatch" target="_blank">closeMatch</a></span>
  <span class="legend-item"><span class="legend-swatch na"></span>k. A.</span>
</div>
<div class="hint">
  Jede Entität wird einmal aufgeführt. Verweist eine Eigenschaft auf eine andere
  Entität, steht der Verweis im <strong>Wertebereich</strong>
  (<span class="entity-ref">Entität</span>) und führt zur Entität weiter unten in
  der Liste.
  Die Spalte <strong>Kardinalität</strong> zeigt die aus
  <code>required</code>, <code>minItems</code> und <code>maxItems</code> abgeleitete
  Kardinalität (<code>n</code> = unbegrenzt).
</div>
<div class="filters">
  <span class="filters-label">Zielschemata:</span>
  {vocab_filters}
  <button type="button" class="filter-btn" data-filter="all">Alle</button>
  <button type="button" class="filter-btn" data-filter="none">Keine</button>
</div>
</div>
<div class="table-wrap">
<table>
<thead>
  <tr><th class="element-name">Eigenschaft</th>{"".join(col_headers)}</tr>
</thead>
<tbody>
{"".join(table_rows)}
</tbody>
</table>
</div>
<div id="tooltip"></div>
<script>
(function() {{
  var tip = document.getElementById('tooltip');
  document.addEventListener('mouseover', function(e) {{
    var el = e.target.closest('.tip');
    if (el && el.dataset.tip) {{
      tip.textContent = el.dataset.tip;
      tip.style.display = 'block';
      var r = el.getBoundingClientRect();
      tip.style.left = r.right + 6 + 'px';
      tip.style.top = r.top - 4 + 'px';
      var tr = tip.getBoundingClientRect();
      if (tr.right > window.innerWidth) {{
        tip.style.left = (r.left - tr.width - 6) + 'px';
      }}
      if (tr.bottom > window.innerHeight) {{
        tip.style.top = (window.innerHeight - tr.height - 8) + 'px';
      }}
    }}
  }});
  document.addEventListener('mouseout', function(e) {{
    if (e.target.closest('.tip')) {{
      tip.style.display = 'none';
    }}
  }});
  // A percentage height does not resolve against a table cell, so stretch the
  // stacked mapping cells to the full row height here.
  function stretchCellStacks() {{
    document.querySelectorAll('td.multi .cell-stack').forEach(function(stack) {{
      stack.style.height = '';
      var cell = stack.parentElement;
      if (cell) {{
        stack.style.height = cell.clientHeight + 'px';
      }}
    }});
  }}
  // Only offer the full-text tooltip when the description is actually clipped.
  function updateDescTips() {{
    document.querySelectorAll('.desc-clip').forEach(function(el) {{
      if (el.scrollHeight > el.clientHeight + 1) {{
        el.classList.add('tip');
      }} else {{
        el.classList.remove('tip');
      }}
    }});
  }}
  function refreshLayout() {{
    measureHeaderOffset();
    stretchCellStacks();
    updateDescTips();
  }}

  // Keep the table header below the sticky page header.
  function measureHeaderOffset() {{
    var header = document.getElementById('page-header');
    if (header) {{
      document.documentElement.style.setProperty('--header-offset', header.offsetHeight + 'px');
    }}
  }}

  // Target-schema filters: show/hide vocabulary columns.
  var VOCAB_WIDTH = 170;
  var filterBoxes = document.querySelectorAll('input[data-vocab-filter]');
  var table = document.querySelector('table');
  var frozenWidth = 0;
  function measureFrozenWidth() {{
    var last = document.querySelector('thead th.description-header');
    if (table && last) {{
      frozenWidth = last.getBoundingClientRect().right - table.getBoundingClientRect().left;
    }}
  }}
  function applyVocabFilters() {{
    var visible = 0;
    filterBoxes.forEach(function(box) {{
      var show = box.checked;
      if (show) {{ visible += 1; }}
      document
        .querySelectorAll('[data-vocab="' + box.getAttribute('data-vocab-filter') + '"]')
        .forEach(function(cell) {{ cell.style.display = show ? '' : 'none'; }});
    }});
    if (table && frozenWidth) {{
      table.style.minWidth = '0';
      table.style.width = frozenWidth + visible * VOCAB_WIDTH + 'px';
    }}
    document.querySelectorAll('.entity-gap td').forEach(function(cell) {{
      cell.colSpan = 4 + visible;
    }});
    refreshLayout();
  }}
  filterBoxes.forEach(function(box) {{
    box.addEventListener('change', applyVocabFilters);
  }});
  document.querySelectorAll('.filter-btn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      var checked = btn.getAttribute('data-filter') === 'all';
      filterBoxes.forEach(function(box) {{ box.checked = checked; }});
      applyVocabFilters();
    }});
  }});
  measureHeaderOffset();
  window.addEventListener('load', function() {{
    measureFrozenWidth();
    applyVocabFilters();
  }});
  window.addEventListener('resize', function() {{
    measureFrozenWidth();
    refreshLayout();
  }});
}})();
</script>
</body>
</html>"""


def main() -> None:
    """Entry point."""
    version_dir = sys.argv[1] if len(sys.argv) > 1 else "v2.0.0"
    repo = SchemaRepository(version_dir)
    rows, mapped_schemas = build_rows(repo)
    columns = ordered_columns(mapped_schemas)
    root = repo.get(ROOT_SCHEMA)
    context = root.get("@context", {})
    schema_id = root.get("$id", "")
    base_url = schema_id.rsplit("/", 1)[0] + "/" if "/" in schema_id else ""
    html = generate_html(rows, columns, context, base_url=base_url)

    out_dir = Path("_build") / version_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "mapping-matrix.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Generated {out_path}")


if __name__ == "__main__":
    main()

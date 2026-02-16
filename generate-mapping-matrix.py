#!/usr/bin/env python3
"""Generate a simple HTML mapping matrix for the QUADRIGA schema."""

import json
import os
import sys
from pathlib import Path


def load_schemas(version_dir):
    """Load all JSON schema files, walk the schema tree in canonical order."""
    version = Path(version_dir)
    cache = {}  # filename -> parsed json

    def get_schema(filename):
        if filename not in cache:
            with open(version / filename) as fh:
                cache[filename] = json.load(fh)
        return cache[filename]

    rows = []  # list of (display_name, x_mappings_dict_or_None, depth, filename)
    mapped_schemas = set()
    visited = set()  # track visited files to avoid duplicates

    # Load @context for resolving prefixed URIs
    root = get_schema("schema.json")
    context = root.get("@context", {})

    def collect_mappings(xm):
        if xm is not None:
            for k in xm:
                if not k.startswith("$"):
                    mapped_schemas.add(k)

    def walk(filename, depth=0):
        """Recursively walk schema following $ref and properties in order."""
        if filename in visited:
            return
        visited.add(filename)

        data = get_schema(filename)
        name = filename.replace(".json", "")
        xm = data.get("x-mappings")
        collect_mappings(xm)
        rows.append((name, xm, depth, filename))

        # Top-level $ref (e.g. author.json -> person.json)
        if "$ref" in data:
            walk(data["$ref"], depth + 1)

        # If it has properties, walk them in definition order
        for prop_name, prop_val in data.get("properties", {}).items():
            if not isinstance(prop_val, dict):
                continue
            # Inline x-mappings on a property (e.g. assessment, date)
            if "x-mappings" in prop_val:
                pxm = prop_val["x-mappings"]
                collect_mappings(pxm)
                rows.append((f"{name}/{prop_name}", pxm, depth + 1, filename))
            # Follow $ref
            if "$ref" in prop_val:
                walk(prop_val["$ref"], depth + 1)

        # If it's an array with items.$ref, follow that
        items = data.get("items", {})
        if isinstance(items, dict) and "$ref" in items:
            walk(items["$ref"], depth)

    # Start from schema.json (the root)
    walk("schema.json")

    # Append any remaining files not reachable from schema.json
    for f in sorted(version.glob("*.json")):
        if f.name not in visited:
            walk(f.name, depth=0)

    return rows, sorted(mapped_schemas), context


def html_escape(text):
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def resolve_uri(target, context):
    """Resolve a prefixed target (e.g. dc:title) to a full URI using @context."""
    if not target:
        return ""
    # Already a full URI
    if target.startswith("http://") or target.startswith("https://"):
        return target
    # Try to resolve prefix
    if ":" in target:
        prefix, local = target.split(":", 1)
        base = context.get(prefix, "")
        if base:
            return base + local
    return ""


def tooltip_icon(comment):
    """Return a tooltip icon span if comment is present, else empty string."""
    if not comment:
        return ""
    return f' <span class="tip" data-tip="{html_escape(comment)}">ⓘ</span>'


def format_sub_cell(entry, context):
    """Format a single mapping entry as a sub-cell div. Returns HTML string."""
    relation = entry.get("relation", "")
    target = entry.get("target", "")
    comment = entry.get("$comment")
    short_rel = relation.replace("skos:", "") if relation else ""
    css_class = short_rel.lower() if short_rel else "unknown"

    if target:
        uri = resolve_uri(target, context)
        if uri:
            target_html = f'<a class="target" href="{html_escape(uri)}" target="_blank">{html_escape(target)}</a>'
        else:
            target_html = f'<span class="target">{html_escape(target)}</span>'
        content = f'<span class="relation">{short_rel}</span><span class="target-line">{target_html}{tooltip_icon(comment)}</span>'
    else:
        content = f'<span class="relation">{short_rel}</span>{tooltip_icon(comment)}'

    return f'<div class="sub-cell {css_class}">{content}</div>'


def cell_content(xm, schema_name, context):
    """Return (html_content, td_css_class) for a given mapping entry."""
    if xm is None:
        return "", "no-mapping"

    entry = xm.get(schema_name)
    if entry is None:
        return "null", "null"

    # Normalize to list
    entries = entry if isinstance(entry, list) else [entry]
    sub_cells = [format_sub_cell(e, context) for e in entries]

    # If single entry, use its color on the td; if multiple, colors are on sub-cells
    if len(entries) == 1:
        rel = entries[0].get("relation", "")
        td_css = rel.replace("skos:", "").lower() if rel else "unknown"
    else:
        td_css = "multi"

    return "".join(sub_cells), td_css


def general_comment(xm):
    """Extract the top-level $comment from x-mappings as a tooltip icon."""
    if xm is None:
        return ""
    comment = xm.get("$comment", "")
    return tooltip_icon(comment)


def generate_html(rows, columns, context):
    """Generate a self-contained HTML string."""
    # Build table rows
    table_rows = []
    for name, xm, depth, filename in rows:
        cells = []
        has_mappings = xm is not None
        for col in columns:
            text, css_class = cell_content(xm, col, context)
            cells.append(f'<td class="{css_class}">{text}</td>')
        comment = general_comment(xm)
        row_class = "no-mappings-row" if not has_mappings else ""
        indent = f'style="padding-left: {8 + depth * 16}px"' if depth > 0 else ""
        element_link = f'<a href="{html_escape(filename)}" target="_blank">{name}</a>'
        table_rows.append(
            f'  <tr class="{row_class}"><td class="element-name" {indent}>{element_link}{comment}</td>{"".join(cells)}</tr>'
        )

    col_headers = "".join(f"<th>{c}</th>" for c in columns)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QUADRIGA Schema – Mapping Matrix</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 1rem;
    background: #fafafa;
  }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.5rem; }}
  .table-wrap {{
    overflow: auto;
    max-height: 90vh;
  }}
  table {{
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  th, td {{
    border: 1.5px solid #999;
    padding: 4px 8px;
    text-align: center;
    white-space: nowrap;
    vertical-align: top;
  }}
  thead th {{
    position: sticky;
    top: 0;
    background: #333;
    color: #fff;
    z-index: 2;
  }}
  .element-name {{
    position: sticky;
    left: 0;
    background: #f0f0f0;
    text-align: left;
    font-weight: 600;
    z-index: 1;
  }}
  thead th:first-child {{
    z-index: 3;
    background: #333;
  }}
  /* relation colors */
  /* Okabe-Ito colorblind-safe palette (lightened for backgrounds) */
  .exactmatch {{ background: #b8e4b2; }}  /* tint of #009E73 bluish green */
  .closematch {{ background: #f5d78e; }}  /* tint of #E69F00 orange */
  .broadmatch {{ background: #f7f0ab; }}  /* tint of #F0E442 yellow */
  .narrowmatch {{ background: #aed5f0; }} /* tint of #56B4E9 sky blue */
  .relatedmatch {{ background: #d9d9d9; }}
  .null {{ background: #f2f2f2; color: #999; }}
  .no-mapping {{ background: #fff; }}
  .sub-cell {{
    padding: 3px 6px;
  }}
  .sub-cell + .sub-cell {{
    border-top: 1px solid #ccc;
  }}
  .multi {{
    padding: 0;
  }}
  .relation {{
    display: block;
    font-size: 0.75em;
    color: #666;
  }}
  .target-line {{
    display: block;
  }}
  a.target {{
    font-weight: 600;
    color: inherit;
    text-decoration: none;
  }}
  a.target:hover {{
    text-decoration: underline;
  }}
  .element-name a {{
    color: inherit;
    text-decoration: none;
  }}
  .element-name a:hover {{
    text-decoration: underline;
  }}
  .tip {{
    cursor: help;
    font-size: 0.85em;
    position: relative;
  }}
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
    margin-bottom: 0.75rem;
    font-size: 0.82rem;
    align-items: center;
  }}
  .legend-item {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }}
  .legend-swatch {{
    width: 14px;
    height: 14px;
    border: 1px solid #bbb;
    border-radius: 2px;
    display: inline-block;
  }}
  .no-mappings-row td {{
    background: #e8e8e8;
    color: #aaa;
  }}
  .no-mappings-row .element-name {{
    background: #e0e0e0;
    color: #999;
  }}
</style>
</head>
<body>
<h1>QUADRIGA Schema – Mapping Matrix</h1>
<div class="legend">
  <span style="font-weight:600">SKOS Relations:</span>
  <span class="legend-item"><span class="legend-swatch" style="background:#b8e4b2"></span> <a href="http://www.w3.org/2004/02/skos/core#exactMatch" target="_blank">exactMatch</a></span>
  <span class="legend-item"><span class="legend-swatch" style="background:#f5d78e"></span> <a href="http://www.w3.org/2004/02/skos/core#closeMatch" target="_blank">closeMatch</a></span>
  <span class="legend-item"><span class="legend-swatch" style="background:#f7f0ab"></span> <a href="http://www.w3.org/2004/02/skos/core#broadMatch" target="_blank">broadMatch</a></span>
  <span class="legend-item"><span class="legend-swatch" style="background:#aed5f0"></span> <a href="http://www.w3.org/2004/02/skos/core#narrowMatch" target="_blank">narrowMatch</a></span>
  <span class="legend-item"><span class="legend-swatch" style="background:#d9d9d9"></span> <a href="http://www.w3.org/2004/02/skos/core#relatedMatch" target="_blank">relatedMatch</a></span>
  <span class="legend-item"><span class="legend-swatch" style="background:#f2f2f2"></span> null</span>
  <span class="legend-item"><span class="legend-swatch" style="background:#e8e8e8"></span> no mapping</span>
</div>
<div class="table-wrap">
<table>
<thead>
  <tr><th class="element-name">Element</th>{col_headers}</tr>
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
      // Keep tooltip on screen
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
}})();
</script>
</body>
</html>"""


def main():
    version_dir = sys.argv[1] if len(sys.argv) > 1 else "v1.0.0"
    rows, columns, context = load_schemas(version_dir)
    html = generate_html(rows, columns, context)

    out_dir = Path("_build") / version_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "mapping-matrix.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Generated {out_path}")


if __name__ == "__main__":
    main()

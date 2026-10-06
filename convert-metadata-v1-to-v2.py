#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Convert a QUADRIGA v1.0.0 ``metadata.yml`` into a v2.0.0 ``quadriga-metadata.yml``.

The QUADRIGA application profile changed its field naming between v1.0.0 and
v2.0.0 (kebab-case to camelCase, list suffixes such as ``*LIST``, split of
``license``/``git``/``url``, structured v1 ``credit`` roles, ...).  This script
performs that mapping and writes a file that is structurally valid against the
v2.0.0 JSON Schema.

Usage:
    uv run convert-metadata-v1-to-v2.py
    uv run convert-metadata-v1-to-v2.py -i metadata.yml -o quadriga-metadata.yml
    uv run convert-metadata-v1-to-v2.py path/to/input.yml path/to/output.yml

The script prints warnings to stderr for information that cannot be carried
over losslessly (e.g. v1 ``supplemented-by`` entries without a URL, or a missing
code license, which is required by v2.0.0).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

SCHEMA_URL = "https://quadriga-dk.github.io/quadriga-schema/v2.0.0/schema.json"

#: Matches a yaml-language-server directive and captures everything but the URL.
LSP_SCHEMA_RE = re.compile(r"(?P<prefix>\$schema=)\S+")

# CRediT roles were allowed as URLs in v1 and are plain strings in v2.
CREDIT_URL_TO_NAME = {
    "https://credit.niso.org/contributor-roles/conceptualization/": "Conceptualization",
    "https://credit.niso.org/contributor-roles/data-curation/": "Data curation",
    "https://credit.niso.org/contributor-roles/formal-analysis/": "Formal analysis",
    "https://credit.niso.org/contributor-roles/funding-acquisition/": "Funding acquisition",
    "https://credit.niso.org/contributor-roles/investigation/": "Investigation",
    "https://credit.niso.org/contributor-roles/methodology/": "Methodology",
    "https://credit.niso.org/contributor-roles/project-administration/": "Project administration",
    "https://credit.niso.org/contributor-roles/resources/": "Resources",
    "https://credit.niso.org/contributor-roles/software/": "Software",
    "https://credit.niso.org/contributor-roles/supervision/": "Supervision",
    "https://credit.niso.org/contributor-roles/validation/": "Validation",
    "https://credit.niso.org/contributor-roles/visualization/": "Visualization",
    "https://credit.niso.org/contributor-roles/writing-original-draft/": (
        "Writing – original draft"
    ),
    "https://credit.niso.org/contributor-roles/writing-review-editing/": (
        "Writing – review & editing"
    ),
}


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


# --------------------------------------------------------------------------
# Person (Author / Contributor)
# --------------------------------------------------------------------------


def convert_person(person: dict[str, Any], role: str) -> dict[str, Any]:
    """Map a v1 person object onto the v2 Author/Contributor shape."""
    if not isinstance(person, dict):
        raise TypeError(f"{role} entry is not a mapping: {person!r}")

    result: dict[str, Any] = {}

    for src, dst in (
        ("family-names", "familyName"),
        ("given-names", "givenName"),
        ("orcid", "orcid"),
        ("affiliation", "affiliation"),
    ):
        if src in person:
            result[dst] = person[src]

    credit = person.get("credit")
    if credit is not None:
        converted = convert_credit(credit, role)
        if converted:
            result["creditLIST"] = converted

    known = {"family-names", "given-names", "orcid", "affiliation", "credit"}
    for key in person:
        if key not in known:
            warn(f"{role}: dropping unknown person field '{key}'")

    return result


def convert_credit(credit: Any, role: str) -> list[str]:
    """v1 credit is a list of strings or {role, degree} objects; v2 wants strings."""
    if not isinstance(credit, list):
        credit = [credit]

    result: list[str] = []
    for entry in credit:
        if isinstance(entry, str):
            result.append(entry)
            continue

        if isinstance(entry, dict):
            raw_role = entry.get("role")
            if raw_role in CREDIT_URL_TO_NAME:
                result.append(CREDIT_URL_TO_NAME[raw_role])
            elif isinstance(raw_role, str):
                result.append(raw_role)
            else:
                warn(f"{role}: dropping unrecognised CRediT role {raw_role!r}")
            if "degree" in entry:
                warn(
                    f"{role}: v2 has no place for CRediT 'degree' "
                    f"({entry.get('degree')!r}); dropped"
                )
            continue

        warn(f"{role}: dropping unsupported CRediT entry {entry!r}")

    return result


# --------------------------------------------------------------------------
# License
# --------------------------------------------------------------------------


def license_to_url(entry: Any, field: str) -> str | None:
    """v1 licenses are a URL string or a {name, url} object; v2 wants a URL."""
    if entry is None:
        return None
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        if "url" in entry:
            return entry["url"]
        warn(f"{field}: license object without 'url'; dropped")
        return None
    warn(f"{field}: unsupported license entry {entry!r}; dropped")
    return None


# --------------------------------------------------------------------------
# Chapters and their sub-entities
# --------------------------------------------------------------------------


def convert_learning_objective(entry: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    if "learning-objective" in entry:
        result["description"] = entry["learning-objective"]

    for src, dst in (
        ("competency", "competency"),
        ("data-flow", "dataFlow"),
        ("blooms-category", "bloomsCategory"),
        ("assessment", "assessment"),
    ):
        if src in entry:
            result[dst] = entry[src]

    known = {"learning-objective", "competency", "data-flow", "blooms-category", "assessment"}
    for key in entry:
        if key not in known:
            warn(f"learning objective: dropping unknown field '{key}'")

    return result


def convert_supplemental_material(item: Any) -> dict[str, Any] | None:
    """Convert one v1 supplemented-by item to a v2 SupplementalMaterial.

    Returns ``None`` when the item is a bare (multilingual) text.  v2 requires a
    ``url`` for supplemental material, so a text-only reference cannot be
    represented and is skipped with a warning.
    """
    if isinstance(item, dict) and "url" in item:
        material: dict[str, Any] = {}
        if "title" in item:
            material["title"] = item["title"]
        material["url"] = item["url"]
        if "note" in item:
            warn("supplemented-by: v2 SupplementalMaterial has no 'note'; dropped")
        for key in item:
            if key not in {"title", "url", "note"}:
                warn(f"supplemented-by: dropping unknown field '{key}'")
        if "title" not in material:
            warn(f"supplemented-by: material for {item['url']!r} has no title")
        return material

    warn(
        "supplemented-by: text-only entry has no URL and cannot be expressed as a "
        f"v2 SupplementalMaterial; dropped ({item!r})"
    )
    return None


def convert_chapter(chapter: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for src, dst in (
        ("title", "title"),
        ("description", "description"),
        ("url", "url"),
        ("time-required", "timeRequired"),
        ("learning-goal", "learningGoal"),
        ("language", "language"),
    ):
        if src in chapter:
            result[dst] = chapter[src]

    objectives = chapter.get("learning-objectives")
    if objectives is not None:
        if not isinstance(objectives, list):
            objectives = [objectives]
        result["learningObjectiveLIST"] = [convert_learning_objective(obj) for obj in objectives]

    supplemented_by = chapter.get("supplemented-by")
    if supplemented_by is not None:
        if not isinstance(supplemented_by, list):
            supplemented_by = [supplemented_by]
        materials = [
            converted
            for item in supplemented_by
            if (converted := convert_supplemental_material(item)) is not None
        ]
        if materials:
            result["supplementalMaterialLIST"] = materials

    known = {
        "title",
        "description",
        "url",
        "time-required",
        "learning-goal",
        "learning-objectives",
        "supplemented-by",
        "language",
    }
    for key in chapter:
        if key not in known:
            warn(f"chapter: dropping unknown field '{key}'")

    return result


def convert_used_tool(tool: Any) -> dict[str, Any] | None:
    """v1 allows a bare URI string or a {name, url} object; v2 requires the object."""
    if isinstance(tool, dict):
        return {"name": tool.get("name"), "url": tool.get("url")}
    if isinstance(tool, str):
        warn(f"used-tools: bare URI {tool!r} converted to a name/url pair")
        return {"name": tool, "url": tool}
    warn(f"used-tools: dropping unsupported entry {tool!r}")
    return None


# --------------------------------------------------------------------------
# Top level
# --------------------------------------------------------------------------


def convert(data: dict[str, Any]) -> dict[str, Any]:
    """Convert a parsed v1 metadata document into a v2.0.0 document."""
    if not isinstance(data, dict):
        raise TypeError("input document must be a mapping")

    # Build the result in the v2 canonical field order.
    result: dict[str, Any] = {}

    if "title" in data:
        result["title"] = data["title"]

    if "authors" in data:
        authors = data["authors"]
        if not isinstance(authors, list):
            authors = [authors]
        result["authorLIST"] = [convert_person(a, "author") for a in authors]

    if "keywords" in data:
        result["keywordLIST"] = data["keywords"]

    for src, dst in (
        ("description", "description"),
        ("table-of-contents", "tableOfContents"),
        ("discipline", "disciplineLIST"),
        ("research-object-type", "researchObjectTypeLIST"),
        ("target-group", "targetGroupLIST"),
        ("time-required", "timeRequired"),
        ("language", "language"),
    ):
        if src in data:
            result[dst] = data[src]

    if "contributors" in data:
        contributors = data["contributors"]
        if not isinstance(contributors, list):
            contributors = [contributors]
        result["contributorLIST"] = [convert_person(c, "contributor") for c in contributors]

    for src, dst in (
        ("identifier", "identifier"),
        ("git", "identifierGit"),
        ("url", "identifierOER"),
    ):
        if src in data:
            result[dst] = data[src]

    if "prerequisites" in data:
        result["prerequisiteLIST"] = data["prerequisites"]

    if "used-tools" in data:
        tools = data["used-tools"]
        if not isinstance(tools, list):
            tools = [tools]
        converted_tools = [
            converted for tool in tools if (converted := convert_used_tool(tool)) is not None
        ]
        if converted_tools:
            result["usedToolLIST"] = converted_tools

    if "chapters" in data:
        chapters = data["chapters"]
        if not isinstance(chapters, list):
            chapters = [chapters]
        result["chapterLIST"] = [convert_chapter(c) for c in chapters]

    for src, dst in (
        ("date-issued", "dateIssued"),
        ("date-modified", "dateModified"),
        ("version", "version"),
        ("context-of-creation", "contextOfCreation"),
        ("quality-assurance", "qualityAssurance"),
        ("learning-resource-type", "learningResourceType"),
    ):
        if src in data:
            result[dst] = data[src]

    # v2 requires exactly "2.0.0".
    result["schemaVersion"] = "2.0.0"

    v1_license = data.get("license")
    if isinstance(v1_license, dict):
        content = license_to_url(v1_license.get("content"), "license.content")
        if content is not None:
            result["license"] = content
        code = license_to_url(v1_license.get("code"), "license.code")
        if code is not None:
            result["licenseCode"] = code
    elif v1_license is not None:
        content = license_to_url(v1_license, "license")
        if content is not None:
            result["license"] = content

    if "license" not in result:
        warn("v1 file has no content license; v2 requires 'license'")
    if "licenseCode" not in result:
        warn(
            "v1 file has no code license; v2 requires 'licenseCode'. Add one to make "
            "the output valid."
        )

    v1_known = {
        "title",
        "authors",
        "keywords",
        "description",
        "table-of-contents",
        "discipline",
        "research-object-type",
        "target-group",
        "time-required",
        "language",
        "contributors",
        "identifier",
        "git",
        "url",
        "prerequisites",
        "used-tools",
        "chapters",
        "date-issued",
        "date-modified",
        "version",
        "context-of-creation",
        "quality-assurance",
        "learning-resource-type",
        "schema-version",
        "license",
    }
    for key in data:
        if key not in v1_known:
            warn(f"dropping unknown top-level field '{key}'")

    return result


# --------------------------------------------------------------------------
# YAML plumbing
# --------------------------------------------------------------------------


def _str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """Render multiline strings as literal blocks for readability."""
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


def lsp_comment(input_path: Path) -> str:
    """Return the input's yaml-language-server comment, updated to the v2 schema.

    The directive is preserved (kept as the first comment) while its ``$schema``
    target is pointed at v2.0.0.  When the input has no such comment, the
    standard v2 directive is emitted.
    """
    try:
        text = input_path.read_text(encoding="utf-8")
    except OSError:
        return f"# yaml-language-server: $schema={SCHEMA_URL}"

    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") and "yaml-language-server" in line and "$schema=" in line:
            return LSP_SCHEMA_RE.sub(rf"\g<prefix>{SCHEMA_URL}", line, count=1)

    return f"# yaml-language-server: $schema={SCHEMA_URL}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Convert a QUADRIGA v1.0.0 metadata.yml to a v2.0.0 quadriga-metadata.yml.")
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="input v1.0.0 metadata file (default: metadata.yml)",
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_opt",
        metavar="INPUT",
        default=None,
        help="input v1.0.0 metadata file (default: metadata.yml)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=("output v2.0.0 metadata file (default: quadriga-metadata.yml beside the input file)"),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the output file if it already exists",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input_opt or args.input or "metadata.yml")
    output_path = (
        Path(args.output) if args.output else input_path.with_name("quadriga-metadata.yml")
    )

    if not input_path.is_file():
        parser.error(f"input file not found: {input_path}")
    if input_path.resolve() == output_path.resolve():
        parser.error("input and output are the same file; refusing to overwrite the v1 metadata")
    if output_path.exists() and not args.force:
        parser.error(f"output file already exists: {output_path} (use --force to overwrite)")

    with input_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    converted = convert(data)

    yaml.add_representer(str, _str_presenter, Dumper=yaml.SafeDumper)
    body = yaml.safe_dump(
        converted,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=100,
    )
    output_path.write_text(f"{lsp_comment(input_path)}\n{body}", encoding="utf-8")

    print(f"wrote {output_path} (from {input_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

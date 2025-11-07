#!/usr/bin/env python3
"""
Validate x-mappings in QUADRIGA schema files against the meta-schema.

This script validates that all x-mappings definitions in JSON schema files
located in directories starting with 'v' (e.g., v1.0.0/) comply with the
x-mappings meta-schema defined in x-mappings-meta-schema.json.

Requirements:
  - Python 3.9+ (uses only standard library)
  - No external dependencies

Usage:
  python3 validate-x-mappings.py

Exit codes:
  0 - All x-mappings are valid
  1 - Validation errors found or script error

Integration:
  This script is automatically run by build-html.sh as a sanity check
  before generating HTML documentation.
"""

import json
import re
import sys
from pathlib import Path


def load_json_file(filepath: Path) -> dict[str, object]:
    """Load and parse a JSON file."""
    try:
        with filepath.open(encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {filepath}: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: Cannot read {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def validate_mapping_entry(entry: object, vocab: str) -> list[str]:
    """Validate a single mapping entry against the meta-schema rules."""
    errors = []

    # Must be null or an object
    if entry is None:
        return errors

    if not isinstance(entry, dict):
        errors.append(f"  {vocab}: must be null or an object, got {type(entry).__name__}")
        return errors

    # Check required properties
    if "relation" not in entry:
        errors.append(f"  {vocab}: missing required property 'relation'")
    if "property" not in entry:
        errors.append(f"  {vocab}: missing required property 'property'")

    # Check for additional properties
    allowed_props = {"relation", "property"}
    extra_props = set(entry.keys()) - allowed_props
    if extra_props:
        errors.append(f"  {vocab}: unexpected properties {extra_props}")

    # Validate relation enum
    if "relation" in entry:
        valid_relations = [
            "skos:exactMatch",
            "skos:closeMatch",
            "skos:broadMatch",
            "skos:narrowMatch",
            "skos:relatedMatch",
        ]
        if not isinstance(entry["relation"], str):
            errors.append(f"  {vocab}.relation: must be a string")
        elif entry["relation"] not in valid_relations:
            errors.append(
                f"  {vocab}.relation: invalid value '{entry['relation']}', "
                f"must be one of {valid_relations}"
            )

    # Validate property pattern
    if "property" in entry:
        if not isinstance(entry["property"], str):
            errors.append(f"  {vocab}.property: must be a string")
        else:
            # Pattern: ^{vocab}:[a-zA-Z]+$ (property must start with the vocabulary namespace)
            pattern = re.compile(rf"^{re.escape(vocab)}:[a-zA-Z]+$")
            if not pattern.match(entry["property"]):
                errors.append(
                    f"  {vocab}.property: '{entry['property']}' does not match "
                    f"pattern '^{vocab}:[a-zA-Z]+$' (must start with vocabulary namespace)"
                )

    return errors


def validate_x_mappings(x_mappings: object) -> list[str]:
    """Validate x-mappings object against the meta-schema."""
    errors = []

    if not isinstance(x_mappings, dict):
        errors.append(f"x-mappings must be an object, got {type(x_mappings).__name__}")
        return errors

    # Check required vocabularies
    required_vocabs = ["dc", "dcterms", "lrmi", "modalia", "schema"]
    missing_vocabs = [vocab for vocab in required_vocabs if vocab not in x_mappings]
    errors.extend(f"Missing required vocabulary: {vocab}" for vocab in missing_vocabs)

    # Check for additional vocabularies
    extra_vocabs = set(x_mappings.keys()) - set(required_vocabs)
    if extra_vocabs:
        errors.append(f"Unexpected vocabularies: {extra_vocabs}")

    # Validate each mapping entry
    for vocab in required_vocabs:
        if vocab in x_mappings:
            entry_errors = validate_mapping_entry(x_mappings[vocab], vocab)
            errors.extend(entry_errors)

    return errors


def find_schema_files() -> list[Path]:
    """Find all JSON schema files in directories starting with 'v'."""
    # Find all directories starting with 'v'
    schema_files = [
        json_file
        for version_dir in Path().glob("v*")
        if version_dir.is_dir()
        for json_file in version_dir.glob("*.json")
    ]

    return sorted(schema_files)


def main() -> int:
    """Validate x-mappings in QUADRIGA schema files."""
    print("Validating x-mappings in QUADRIGA schema files...\n")

    schema_files = find_schema_files()

    if not schema_files:
        print("No schema files found in directories starting with 'v'")
        return 0

    print(f"Found {len(schema_files)} schema files to check\n")

    total_errors = 0
    files_with_mappings = 0
    files_validated = 0

    for filepath in schema_files:
        schema = load_json_file(filepath)

        # Check if this schema has x-mappings
        if "x-mappings" not in schema:
            continue

        files_with_mappings += 1
        errors = validate_x_mappings(schema["x-mappings"])

        if errors:
            print(f"❌ {filepath}:")
            for error in errors:
                print(f"  {error}")
            print()
            total_errors += len(errors)
        else:
            files_validated += 1

    # Summary
    print("=" * 60)
    print("Validation complete:")
    print(f"  Files checked: {len(schema_files)}")
    print(f"  Files with x-mappings: {files_with_mappings}")
    print(f"  Files validated successfully: {files_validated}")
    print(f"  Files with errors: {files_with_mappings - files_validated}")
    print(f"  Total errors: {total_errors}")
    print("=" * 60)

    if total_errors > 0:
        print("\n❌ Validation FAILED")
        return 1

    print("\n✅ All x-mappings are valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

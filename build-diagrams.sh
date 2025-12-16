#!/bin/bash
# Build all PlantUML diagrams to PNG files
#
# Requires: plantuml
# Install: brew install plantuml

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAGRAMS_DIR="${SCRIPT_DIR}/diagrams"

# Check if plantuml is installed
if ! command -v plantuml &>/dev/null; then
    echo "Error: plantuml is not installed."
    echo "Install with: brew install plantuml"
    exit 1
fi

# Check if diagrams directory exists
if [ ! -d "${DIAGRAMS_DIR}" ]; then
    echo "Error: diagrams directory not found at ${DIAGRAMS_DIR}"
    exit 1
fi

# Output directory for PNG files
OUTPUT_DIR="${DIAGRAMS_DIR}/png"
mkdir -p "${OUTPUT_DIR}"

# Count files
total=$(find "${DIAGRAMS_DIR}" -maxdepth 1 -name "*.puml" | wc -l | tr -d ' ')
count=0

echo "Building ${total} diagrams..."

# Build each diagram (scale and DPI configured in .puml files)
for file in "${DIAGRAMS_DIR}"/*.puml; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        count=$((count + 1))
        echo "[${count}/${total}] ${filename}"
        PLANTUML_LIMIT_SIZE=8192 plantuml -tpng -o png "$file"
    fi
done

echo "Done. Built ${count} diagrams."

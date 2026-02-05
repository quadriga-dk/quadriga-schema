#!/bin/bash
# Build all PlantUML diagrams to PNG files
#
# Requires: Docker (recommended) or plantuml
# Docker ensures consistent output across local and CI environments
#
# Usage:
#   ./build-diagrams.sh          # Auto-detect (prefer Docker)
#   ./build-diagrams.sh --docker # Force Docker
#   ./build-diagrams.sh --local  # Force local plantuml

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAGRAMS_DIR="${SCRIPT_DIR}/diagrams"
# Pin version for reproducible builds (update manually when needed)
PLANTUML_VERSION="1.2026.1"
PLANTUML_IMAGE="plantuml/plantuml:${PLANTUML_VERSION}"

# Parse arguments
USE_DOCKER=""
case "${1:-}" in
--docker) USE_DOCKER="true" ;;
--local) USE_DOCKER="false" ;;
"")
	# Auto-detect: prefer Docker if available and running
	if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
		USE_DOCKER="true"
	elif command -v plantuml &>/dev/null; then
		USE_DOCKER="false"
	else
		echo "Error: Neither Docker nor plantuml is available."
		echo "Install Docker or run: brew install plantuml"
		exit 1
	fi
	;;
*)
	echo "Usage: $0 [--docker|--local]"
	exit 1
	;;
esac

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

if [ "$USE_DOCKER" = "true" ]; then
	echo "Building ${total} diagrams using Docker (${PLANTUML_IMAGE})..."

	# Pull image if not present
	if ! docker image inspect "${PLANTUML_IMAGE}" &>/dev/null; then
		echo "Pulling Docker image..."
		docker pull "${PLANTUML_IMAGE}"
	fi

	# Build each diagram
	for file in "${DIAGRAMS_DIR}"/*.puml; do
		if [ -f "$file" ]; then
			filename=$(basename "$file")
			count=$((count + 1))
			echo "[${count}/${total}] ${filename}"
			docker run --rm \
				-v "${DIAGRAMS_DIR}:/data" \
				-e PLANTUML_LIMIT_SIZE=8192 \
				"${PLANTUML_IMAGE}" \
				-tpng -o /data/png "/data/${filename}"
		fi
	done
else
	echo "Building ${total} diagrams using local plantuml..."

	# Verify plantuml is installed
	if ! command -v plantuml &>/dev/null; then
		echo "Error: plantuml is not installed."
		echo "Install with: brew install plantuml"
		exit 1
	fi

	# Build each diagram (scale and DPI configured in .puml files)
	for file in "${DIAGRAMS_DIR}"/*.puml; do
		if [ -f "$file" ]; then
			filename=$(basename "$file")
			count=$((count + 1))
			echo "[${count}/${total}] ${filename}"
			PLANTUML_LIMIT_SIZE=8192 plantuml -tpng -o png "$file"
		fi
	done
fi

echo "Done. Built ${count} diagrams."

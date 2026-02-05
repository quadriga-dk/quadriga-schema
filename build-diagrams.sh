#!/bin/bash
# Build PlantUML diagrams to PNG files
#
# Requires: Docker (recommended) or plantuml
# Docker ensures consistent output across local and CI environments
#
# Usage:
#   ./build-diagrams.sh                    # Build all diagrams (auto-detect)
#   ./build-diagrams.sh overview           # Build only overview.puml
#   ./build-diagrams.sh --docker           # Force Docker for all
#   ./build-diagrams.sh --local            # Force local plantuml for all
#   ./build-diagrams.sh --docker overview  # Force Docker for single diagram
#   ./build-diagrams.sh --local overview   # Force local for single diagram

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAGRAMS_DIR="${SCRIPT_DIR}/diagrams"
# Pin version for reproducible builds (update manually when needed)
PLANTUML_VERSION="1.2026.1"
PLANTUML_IMAGE="plantuml/plantuml:${PLANTUML_VERSION}"

# Parse arguments
USE_DOCKER=""
SINGLE_DIAGRAM=""

while [[ $# -gt 0 ]]; do
	case "$1" in
	--docker)
		USE_DOCKER="true"
		shift
		;;
	--local)
		USE_DOCKER="false"
		shift
		;;
	-h | --help)
		echo "Usage: $0 [--docker|--local] [diagram-name]"
		echo ""
		echo "Options:"
		echo "  --docker    Force Docker for building"
		echo "  --local     Force local plantuml"
		echo "  -h, --help  Show this help message"
		echo ""
		echo "Arguments:"
		echo "  diagram-name  Name of a single diagram to build (without .puml extension)"
		echo "                If omitted, all diagrams are built."
		echo ""
		echo "Examples:"
		echo "  $0                    # Build all diagrams"
		echo "  $0 overview           # Build only overview.puml"
		echo "  $0 --docker overview  # Build overview.puml using Docker"
		exit 0
		;;
	-*)
		echo "Unknown option: $1"
		echo "Usage: $0 [--docker|--local] [diagram-name]"
		exit 1
		;;
	*)
		# Positional argument: diagram name
		SINGLE_DIAGRAM="$1"
		shift
		;;
	esac
done

# Auto-detect Docker vs local if not specified
if [ -z "$USE_DOCKER" ]; then
	if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
		USE_DOCKER="true"
	elif command -v plantuml &>/dev/null; then
		USE_DOCKER="false"
	else
		echo "Error: Neither Docker nor plantuml is available."
		echo "Install Docker or run: brew install plantuml"
		exit 1
	fi
fi

# Check if diagrams directory exists
if [ ! -d "${DIAGRAMS_DIR}" ]; then
	echo "Error: diagrams directory not found at ${DIAGRAMS_DIR}"
	exit 1
fi

# Output directory for PNG files
OUTPUT_DIR="${DIAGRAMS_DIR}/png"
mkdir -p "${OUTPUT_DIR}"

# Determine which files to build
if [ -n "$SINGLE_DIAGRAM" ]; then
	# Build single diagram
	TARGET_FILE="${DIAGRAMS_DIR}/${SINGLE_DIAGRAM}.puml"
	if [ ! -f "$TARGET_FILE" ]; then
		echo "Error: Diagram not found: ${TARGET_FILE}"
		echo ""
		echo "Available diagrams:"
		for f in "${DIAGRAMS_DIR}"/*.puml; do
			[ -f "$f" ] && echo "  $(basename "$f" .puml)"
		done
		exit 1
	fi
	FILES_TO_BUILD=("$TARGET_FILE")
	total=1
else
	# Build all diagrams
	FILES_TO_BUILD=("${DIAGRAMS_DIR}"/*.puml)
	total=$(find "${DIAGRAMS_DIR}" -maxdepth 1 -name "*.puml" | wc -l | tr -d ' ')
fi

count=0

if [ "$USE_DOCKER" = "true" ]; then
	echo "Building ${total} diagram(s) using Docker (${PLANTUML_IMAGE})..."

	# Pull image if not present
	if ! docker image inspect "${PLANTUML_IMAGE}" &>/dev/null; then
		echo "Pulling Docker image..."
		docker pull "${PLANTUML_IMAGE}"
	fi

	# Build each diagram
	for file in "${FILES_TO_BUILD[@]}"; do
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
	echo "Building ${total} diagram(s) using local plantuml..."

	# Verify plantuml is installed
	if ! command -v plantuml &>/dev/null; then
		echo "Error: plantuml is not installed."
		echo "Install with: brew install plantuml"
		exit 1
	fi

	# Build each diagram (scale and DPI configured in .puml files)
	for file in "${FILES_TO_BUILD[@]}"; do
		if [ -f "$file" ]; then
			filename=$(basename "$file")
			count=$((count + 1))
			echo "[${count}/${total}] ${filename}"
			PLANTUML_LIMIT_SIZE=8192 plantuml -tpng -o png "$file"
		fi
	done
fi

echo "Done. Built ${count} diagram(s)."

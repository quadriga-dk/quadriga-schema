# Justfile for QUADRIGA schema
# https://just.systems

set shell := ["bash", "-euo", "pipefail", "-c"]

# PlantUML configuration
plantuml_version := trim(read(".plantuml-version"))
plantuml_image := "plantuml/plantuml:" + plantuml_version
diagrams_dir := justfile_directory() / "diagrams"
build_dir := "_build"

# Default recipe: show available recipes
default:
    @just --list --unsorted

# ─── Validation ───────────────────────────────────────────

# Validate x-mappings in all schema files
[group('build')]
validate:
    python3 validate-x-mappings.py

# ─── Diagrams ────────────────────────────────────────────

# Build all PlantUML diagrams (use "list" to list available diagrams)
[group('diagrams')]
diagrams engine="auto":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{ engine }}" = "list" ]; then
        for f in "{{ diagrams_dir }}"/*.puml; do basename "$f" .puml; done
        exit 0
    fi
    just _diagrams-resolve-engine "{{ engine }}" ""

# Build a single PlantUML diagram by name (use "list" to list available diagrams)
[group('diagrams')]
diagram name="list" engine="auto":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{ name }}" = "list" ]; then
        for f in "{{ diagrams_dir }}"/*.puml; do basename "$f" .puml; done
        exit 0
    fi
    just _diagrams-resolve-engine "{{ engine }}" "{{ name }}"

# [private] Resolve engine (auto-detect or validate) then run
_diagrams-resolve-engine engine name="":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{ engine }}" in
        docker|local)
            just _diagrams-run "{{ engine }}" "{{ name }}"
            ;;
        auto)
            if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
                just _diagrams-run docker "{{ name }}"
            elif command -v plantuml &>/dev/null; then
                just _diagrams-run local "{{ name }}"
            else
                echo "Error: Neither Docker nor plantuml is available."
                echo "Install Docker or run: brew install plantuml"
                exit 1
            fi
            ;;
        *)
            echo "Error: Unknown engine '{{ engine }}'. Use: auto, docker, local"
            exit 1
            ;;
    esac

# [private] Build diagrams with specified engine (docker|local)
_diagrams-run engine name="":
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "{{ diagrams_dir }}/png"

    # Verify engine availability
    if [ "{{ engine }}" = "docker" ]; then
        if ! command -v docker &>/dev/null || ! docker info &>/dev/null 2>&1; then
            echo "Error: Docker is not available."
            exit 1
        fi
    else
        if ! command -v plantuml &>/dev/null; then
            echo "Error: plantuml is not installed."
            echo "Install with: brew install plantuml"
            exit 1
        fi
    fi

    # Determine which files to build
    if [ -n "{{ name }}" ]; then
        target="{{ diagrams_dir }}/{{ name }}.puml"
        if [ ! -f "$target" ]; then
            echo "Error: Diagram not found: $target"
            echo ""
            echo "Available diagrams:"
            just diagrams-list
            exit 1
        fi
        files=("$target")
    else
        files=("{{ diagrams_dir }}"/*.puml)
    fi

    total=${#files[@]}

    if [ "{{ engine }}" = "docker" ]; then
        echo "Building ${total} diagram(s) using Docker ({{ plantuml_image }})..."
        # Pull image if not present
        if ! docker image inspect "{{ plantuml_image }}" &>/dev/null; then
            echo "Pulling Docker image..."
            docker pull "{{ plantuml_image }}"
        fi
    else
        echo "Building ${total} diagram(s) using local plantuml..."
    fi

    count=0
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            count=$((count + 1))
            echo "[${count}/${total}] ${filename}"
            if [ "{{ engine }}" = "docker" ]; then
                docker run --rm \
                    -v "{{ diagrams_dir }}:/data" \
                    -e PLANTUML_LIMIT_SIZE=8192 \
                    "{{ plantuml_image }}" \
                    -tpng -o /data/png "/data/${filename}"
            else
                PLANTUML_LIMIT_SIZE=8192 plantuml -tpng -o png "$file"
            fi
        fi
    done
    echo "Done. Built ${count} diagram(s)."

# ─── Mapping Matrix ───────────────────────────────────────

# Generate mapping matrix HTML for all schema versions
[group('build')]
mapping-matrix engine="auto":
    #!/usr/bin/env bash
    set -euo pipefail

    run_generator() {
        local version_dir="$1"
        if [ "$2" = "docker" ]; then
            docker run --rm \
                --user "$(id -u):$(id -g)" \
                -v "{{ justfile_directory() }}:/work" \
                -w /work \
                python:3-slim \
                python3 generate-mapping-matrix.py "$version_dir"
        else
            python3 generate-mapping-matrix.py "$version_dir"
        fi
    }

    resolve_engine() {
        case "{{ engine }}" in
            docker)  echo docker ;;
            local)   echo local ;;
            auto)
                if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
                    echo docker
                elif command -v python3 &>/dev/null; then
                    echo local
                else
                    echo "Error: Neither Docker nor Python 3 is available." >&2
                    exit 1
                fi
                ;;
            *)
                echo "Error: Unknown engine '{{ engine }}'. Use: auto, docker, local" >&2
                exit 1
                ;;
        esac
    }

    resolved=$(resolve_engine)
    echo "Generating mapping matrices using $resolved..."

    for version_dir in v*/; do
        if [ -d "$version_dir" ] && [ -f "$version_dir/schema.json" ]; then
            echo "  $version_dir"
            run_generator "$version_dir" "$resolved"
        fi
    done

    # Generate for latest/
    if [ -f "latest/schema.json" ]; then
        echo "  latest/"
        run_generator "latest" "$resolved"
    fi

    echo "Done."

# ─── HTML Documentation ─────────────────────────────────

# Build HTML documentation (validates first, then generates)
[group('build')]
html: validate mapping-matrix
    #!/usr/bin/env bash
    set -euo pipefail

    # Re-serialize a JSON file with ASCII-only encoding (non-ASCII → \uXXXX)
    # so browsers display characters correctly without charset header control.
    copy_json_ascii() {
        local src="$1" dest="$2"
        python3 ascii-escape-json.py "$src" "$dest"
    }

    # Copy a directory tree, ASCII-escaping all .json files
    copy_dir_ascii_json() {
        local src="$1" dest="$2"
        mkdir -p "$dest"
        # Copy everything except .json files first
        find "$src" -mindepth 1 -not -name '*.json' | while read -r item; do
            local rel="${item#$src/}"
            if [ -d "$item" ]; then
                mkdir -p "$dest/$rel"
            else
                cp "$item" "$dest/$rel"
            fi
        done
        # Copy .json files with ASCII escaping
        find "$src" -name '*.json' | while read -r json_file; do
            local rel="${json_file#$src/}"
            mkdir -p "$(dirname "$dest/$rel")"
            copy_json_ascii "$json_file" "$dest/$rel"
        done
    }

    # Create extensionless redirect files for all .json files in a directory
    create_redirects() {
        local dir="$1"
        for json_file in "$dir"/*.json; do
            if [ -f "$json_file" ]; then
                local name
                name=$(basename "$json_file" .json)
                echo "<meta http-equiv=\"Refresh\" content=\"0; url=${name}.json\" />" > "$dir/$name"
            fi
        done
    }

    echo "Building HTML for QUADRIGA schema versions..."

    # Create build directory
    mkdir -p "{{ build_dir }}"

    # Create root index.html that redirects to latest
    echo '<meta http-equiv="Refresh" content="0; url=latest/schema.html" />' > "{{ build_dir }}/index.html"

    # Build HTML for each version folder
    for version_dir in v*/; do
        if [ -d "$version_dir" ] && [ -f "$version_dir/schema.json" ]; then
            echo "Building HTML for $version_dir"
            mkdir -p "{{ build_dir }}/$version_dir"
            generate-schema-doc \
                --config custom_template_path=templates/js/base.html \
                --config link_to_reused_ref=false \
                "$version_dir/schema.json" "{{ build_dir }}/$version_dir/schema.html"
            echo '<meta http-equiv="Refresh" content="0; url=schema.html" />' > "{{ build_dir }}/$version_dir/index.html"
        fi
    done

    # Build HTML for latest (symlink)
    if [ -f "latest/schema.json" ]; then
        echo "Building HTML for latest"
        mkdir -p "{{ build_dir }}/latest"
        generate-schema-doc \
            --config custom_template_path=templates/js/base.html \
            --config link_to_reused_ref=false \
            "latest/schema.json" "{{ build_dir }}/latest/schema.html"
        echo '<meta http-equiv="Refresh" content="0; url=schema.html" />' > "{{ build_dir }}/latest/index.html"
    fi

    # Copy all version folders with their JSON files (ASCII-escaped)
    echo "Copying version folders..."
    for version_dir in v*/; do
        if [ -d "$version_dir" ]; then
            copy_dir_ascii_json "${version_dir%/}" "{{ build_dir }}/${version_dir%/}"
            create_redirects "{{ build_dir }}/${version_dir%/}"
        fi
    done

    # Copy latest folder contents (HTML was already built, now copy JSON files)
    echo "Copying latest folder JSON files (ASCII-escaped)..."
    for json_file in latest/*.json; do
        copy_json_ascii "$json_file" "{{ build_dir }}/latest/$(basename "$json_file")"
    done
    create_redirects "{{ build_dir }}/latest"

    # Copy examples
    echo "Copying examples..."
    cp -r examples "{{ build_dir }}/"

    # Copy diagrams
    echo "Copying diagrams..."
    mkdir -p "{{ build_dir }}/diagrams"
    cp diagrams/png/*.png "{{ build_dir }}/diagrams/"
    cp diagrams/index.html "{{ build_dir }}/diagrams/"

    echo "Build complete! Output in {{ build_dir }}/"

# ─── Combined ───────────────────────────────────────────

# Build everything: diagrams + HTML docs
[group('build')]
build: diagrams html

# ─── Development ─────────────────────────────────────────

# Serve built HTML documentation locally
[group('build')]
serve port="8000":
    @echo "Serving {{ build_dir }}/ at http://localhost:{{ port }}"
    python3 -m http.server {{ port }} -d "{{ build_dir }}"

# Clean build artifacts
[group('build')]
clean:
    rm -rf "{{ build_dir }}"

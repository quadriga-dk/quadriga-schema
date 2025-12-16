#!/bin/bash
# Build HTML versions of QUADRIGA schema
# This script can be run locally to generate the same HTML output as the GitHub Actions workflow

set -e  # Exit on error

# Function to create HTML redirect files for extensionless URLs
# Usage: create_extensionless_redirects <directory>
create_extensionless_redirects() {
  local dir="$1"
  for json_file in "$dir"*.json; do
    if [ -f "$json_file" ]; then
      basename_no_ext=$(basename "$json_file" .json)
      echo "<meta http-equiv=\"Refresh\" content=\"0; url=${basename_no_ext}.json\" />" > "${dir}${basename_no_ext}"
    fi
  done
}

# Validate x-mappings before building
echo "Validating x-mappings..."
python3 validate-x-mappings.py
if [ $? -ne 0 ]; then
  echo "ERROR: x-mappings validation failed. Please fix the errors before building."
  exit 1
fi
echo ""

echo "Building HTML for QUADRIGA schema versions..."

# Create build directory
mkdir -p _build

# Create root index.html that redirects to latest
echo '<meta http-equiv="Refresh" content="0; url=latest/schema.html" />' > _build/index.html

# Build HTML for each version folder
for version_dir in v*/; do
  if [ -d "$version_dir" ] && [ -f "$version_dir/schema.json" ]; then
    echo "Building HTML for $version_dir"
    mkdir -p "_build/$version_dir"
    generate-schema-doc --config custom_template_path=templates/js/base.html --config link_to_reused_ref=false "$version_dir/schema.json" "_build/$version_dir/schema.html"
    # Create index.html redirect in version folder
    echo '<meta http-equiv="Refresh" content="0; url=schema.html" />' > "_build/$version_dir/index.html"
  fi
done

# Build HTML for latest (symlink)
if [ -f "latest/schema.json" ]; then
  echo "Building HTML for latest"
  mkdir -p "_build/latest"
  generate-schema-doc --config custom_template_path=templates/js/base.html --config link_to_reused_ref=false "latest/schema.json" "_build/latest/schema.html"
  # Create index.html redirect in latest folder
  echo '<meta http-equiv="Refresh" content="0; url=schema.html" />' > "_build/latest/index.html"
fi

# Copy all version folders with their JSON files
echo "Copying version folders..."
for version_dir in v*/; do
  if [ -d "$version_dir" ]; then
    cp -r "$version_dir" _build/
    # Create HTML redirect files for extensionless URLs in version folders
    create_extensionless_redirects "_build/${version_dir}"
  fi
done

# Copy latest folder contents (HTML was already built, now copy JSON files)
echo "Copying latest folder JSON files..."
cp latest/*.json _build/latest/

# Create HTML redirect files for extensionless URLs
echo "Creating redirect files for extensionless URLs..."
create_extensionless_redirects "_build/latest/"

# Copy examples
echo "Copying examples..."
cp -r examples _build/

# Copy diagrams
echo "Copying diagrams..."
mkdir -p _build/diagrams
cp diagrams/png/*.png _build/diagrams/
cp diagrams/index.html _build/diagrams/

echo "Build complete! Output in _build/"

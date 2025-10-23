#!/bin/bash
# Build HTML versions of QUADRIGA schema
# This script can be run locally to generate the same HTML output as the GitHub Actions workflow

set -e  # Exit on error

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
    generate-schema-doc --config template_name=js "$version_dir/schema.json" "_build/$version_dir/schema.html"
    # Create index.html redirect in version folder
    echo '<meta http-equiv="Refresh" content="0; url=schema.html" />' > "_build/$version_dir/index.html"
  fi
done

# Build HTML for latest (symlink)
if [ -f "latest/schema.json" ]; then
  echo "Building HTML for latest"
  mkdir -p "_build/latest"
  generate-schema-doc --config template_name=js "latest/schema.json" "_build/latest/schema.html"
  # Create index.html redirect in latest folder
  echo '<meta http-equiv="Refresh" content="0; url=schema.html" />' > "_build/latest/index.html"
fi

# Copy all version folders with their JSON files
echo "Copying version folders..."
for version_dir in v*/; do
  if [ -d "$version_dir" ]; then
    cp -r "$version_dir" _build/
  fi
done

# Copy latest folder contents (HTML was already built, now copy JSON files)
echo "Copying latest folder JSON files..."
cp latest/*.json _build/latest/

# Copy examples
echo "Copying examples..."
cp -r examples _build/

echo "Build complete! Output in _build/"

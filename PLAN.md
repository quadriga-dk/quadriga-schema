# Plan: X-Mapping Matrix HTML Generator

Generate an interactive HTML matrix page showing all schema elements (entities
& properties) vs. mapped schemas (x-mappings), with SKOS relations and targets
in cells. Deployed per schema version via GitHub Pages.

## Context

- **Schema location**: `v1.0.0/*.json` (44 files with `x-mappings`, 7
  entity-type objects with properties)
- **Mapped schemas (columns)**: `dc`, `dcat`, `dcterms`, `hermes`, `lrmi`,
  `modalia`, `schema`
- **Entities** (objects with properties): `schema`, `chapter`,
  `learning-objectives-entry`, `license`, `person`, `quality-assurance`,
  `supplemental-material`
- **Cell content**: SKOS relation + target, or explicit `null`
- **Build system**: `justfile` with Docker-preferred pattern (see diagrams
  recipe), deployed via GitHub Actions to GitHub Pages
- **Existing deployment**: `_build/` → GitHub Pages at
  `quadriga-dk.github.io/quadriga-schema/`

## Tasks

### 1. Create the generator script (`generate-mapping-matrix.py`)

- [ ] **1.1** Create `generate-mapping-matrix.py` that accepts a version
      directory as argument (e.g., `v1.0.0/`)
- [ ] **1.2** Parse all `*.json` schema files, build a data model:
  - Identify entities (objects with `properties`) vs. leaf properties
  - Resolve `$ref` links to build parent→child hierarchy
  - Collect `x-mappings` from each file (top-level) and from nested properties
    (e.g., `learning-objectives-entry/assessment`, `quality-assurance/date`)
  - Collect all unique mapping schema names for column headers
- [ ] **1.3** Build **two row orderings** (togglable in the HTML):
  - **Hierarchical view**: Recursive tree rooted at `schema.json` → its
    properties → their sub-properties (full nesting depth)
  - **Logical entity view**: Flat groups where each entity (`schema`,
    `chapter`, `person`, `learning-objectives-entry`, `license`,
    `quality-assurance`, `supplemental-material`) is a top-level section at the
    same level, each with its own properties beneath it
- [ ] **1.4** Output a single self-contained HTML file (no external
      dependencies)

### 2. HTML structure & interactivity

- [ ] **2.1** **Matrix table**:
  - Sticky header row with mapped schema names as columns
  - Sticky first column (element names) for horizontal scroll
  - Rows = schema elements, indented/grouped by parent entity
  - Cells = SKOS relation + target URI/term
- [ ] **2.2** **Null / no-mapping handling**:
  - `null` x-mappings: show explicit "—" or "null" marker in cell (clearly
    visible, not just empty)
  - Properties/files that have **no `x-mappings` at all**: entire row greyed
    out
- [ ] **2.3** **Color-coding** by SKOS relation type:
  - `skos:exactMatch` → green
  - `skos:closeMatch` → yellow/amber
  - `skos:broadMatch` → orange
  - `skos:narrowMatch` → blue
  - `skos:relatedMatch` → grey
  - `null` → muted/light background
- [ ] **2.4** **Collapsible/foldable rows** (entity sections):
  - Each entity group can be collapsed to hide its child properties
  - JS-based toggle with expand/collapse all buttons
- [ ] **2.5** **Collapsible/foldable columns** (mapped schemas):
  - Each mapped schema column can be individually hidden/shown
  - Column toggle controls (e.g., checkboxes or buttons above the table)
- [ ] **2.6** **View toggle**: Switch between hierarchical and logical entity
      ordering
- [ ] **2.7** **`$comment` tooltips**: Hover on a cell to see any `$comment`
      from the x-mappings object
- [ ] **2.8** **Scrollability**: Horizontal + vertical scroll with sticky first
      column and header row

### 3. Integrate into `justfile` (Docker-preferred)

- [ ] **3.1** Add `just mapping-matrix` recipe that:
  - Uses Docker if available (Python container), falls back to local Python
  - Follows the same `auto/docker/local` engine pattern as the `diagrams`
    recipe
  - Runs `generate-mapping-matrix.py` for each version directory
- [ ] **3.2** Output to `_build/<version>/mapping-matrix.html` for each version
- [ ] **3.3** Also generate for `latest/`

### 4. Integrate into build pipeline

- [ ] **4.1** Add `mapping-matrix` as a dependency of the `html` recipe (or
      `build`), so it's generated alongside existing HTML docs
- [ ] **4.2** Update GitHub Actions workflow to include matrix generation (if
      not already covered by `just html`)
- [ ] **4.3** Ensure the matrix HTML is included in the `_build/` artifact
      uploaded to GitHub Pages

### 5. Update README

- [ ] **5.1** Add a section or link under the existing "Vocabulary Mappings
      (x-mappings)" section in `README.md` pointing to the deployed matrix page:
  - Link:
    `https://quadriga-dk.github.io/quadriga-schema/latest/mapping-matrix.html`
  - Brief description of what the matrix shows
- [ ] **5.2** Document how to build the matrix locally (`just mapping-matrix`)

### 6. Testing & polish

- [ ] **6.1** Verify all 44 schema files with x-mappings are represented
- [ ] **6.2** Verify nested property-level mappings appear correctly
      (`assessment`, `date`)
- [ ] **6.3** Verify elements without x-mappings (e.g.,
      `multilingual-text.json`, `semver.json`) are greyed out
- [ ] **6.4** Test both view modes (hierarchical vs. logical entity)
- [ ] **6.5** Test column fold/unfold
- [ ] **6.6** Test row fold/unfold for each entity group
- [ ] **6.7** Test scrolling with sticky headers/columns
- [ ] **6.8** Test in Docker and local Python execution

## Notes

- **Docker pattern**: Follow existing `_diagrams-resolve-engine` pattern with
  `auto/docker/local` engine selection
- **7 mapped schema vocabularies**: dc, dcat, dcterms, hermes, lrmi, modalia,
  schema
- **7 entities** (objects with properties): schema, chapter,
  learning-objectives-entry, license, person, quality-assurance,
  supplemental-material
- **Logical entity view**: Entities like `chapter` and `supplemental-material`
  (which are deeply nested under `schema` → `chapters` → items) should be
  elevated to top-level sections alongside `schema` itself, each showing their
  own property subtrees
- The script should be pure Python with no external dependencies (just stdlib
  `json`, `os`, `pathlib`) so it runs easily in any Python container

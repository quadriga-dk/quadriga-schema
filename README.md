# QUADRIGA Application Profile

[![DOI](https://zenodo.org/badge/1007838017.svg)](https://doi.org/10.5281/zenodo.18184772)

**Table of Contents**

- [QUADRIGA Application Profile](#quadriga-application-profile)
  - [About This Repository](#about-this-repository)
  - [Structure of the Application Profile](#structure-of-the-application-profile)
    - [Canonical order of the elements in `quadriga-metadata.yml`](#canonical-order-of-the-elements-in-quadriga-metadatayml)
    - [Diagrams](#diagrams)
  - [Usage](#usage)
    - [Creating Metadata Files](#creating-metadata-files)
    - [Migrating from v1.0.0 to v2.0.0](#migrating-from-v100-to-v200)
    - [Vocabulary Mappings (x-mappings)](#vocabulary-mappings-x-mappings)
      - [Structure](#structure)
      - [Target Vocabularies](#target-vocabularies)
      - [SKOS Relation Types](#skos-relation-types)
      - [Mapping Matrix](#mapping-matrix)
      - [Meta-Schema](#meta-schema)
  - [Documentation](#documentation)

The QUADRIGA Application Profile is a JSON-Schema designed for describing Open
Educational Resources (OER) in German academic contexts. It provides structured
metadata for learning materials, integrating competency frameworks, Bloom's
taxonomy, and multilingual support to enable comprehensive resource description
and discovery. It is used primarily within QUADRIGA as ground truth within a
Jupyter Book repository and to allow the Navigator to ingest this metadata for
retrieval purposes.

The application profile emphasizes semantic web compatibility through [Dublin
Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) and
[Schema.org](https://schema.org/) mappings, while supporting structured person
representation, learning objectives tracking, and quality assurance workflows
tailored for educational content creation and management.

## About This Repository

This repository contains the complete QUADRIGA application profile definition split into
modular JSON files for maintainability. It features a versioning system with one directory
per profile version (`v1.0.0`, `v2.0.0`) and a `latest` symlink pointing to the current
stable version (currently `v2.0.0`), automated HTML documentation generation via GitHub
Actions, and deployment to GitHub Pages for easy access and reference.

**Entry Point:** `schema.json` in each version directory (e.g.
[`v2.0.0/schema.json`](./v2.0.0/schema.json), or
[`latest/schema.json`](./latest/schema.json) for the stable version)

**Licensing:** The application profile is licensed under CC0 (see `LICENSE-SCHEMA.txt`). Any
code in this repository is licensed under MIT (see `LICENSE-CODE.txt`).

**Archiving:** The application profile is archived on Zenodo for long-term preservation and
citable DOI assignment. Zenodo metadata is maintained in `.zenodo.json`.

## Structure of the Application Profile

The application profile describes educational resources with the following key components
(field names as of v2.0.0):

- **Basic metadata**: Title, description, identifiers (`identifier`, `identifierGit`,
  `identifierOER`), publication dates, and versioning
- **Authors and contributors**: Structured person information (`authorLIST`,
  `contributorLIST`) with [ORCID](https://orcid.org/), [CRediT](https://credit.niso.org)
  roles (`creditLIST`), and affiliation
- **Content organization**: Chapter-based structure (`chapterLIST`) with overarching
  learning goals (`learningGoal`) and individual learning objectives
  (`learningObjectiveLIST`)
- **Competency mapping**: Integration with [QUADRIGA data literacy
  framework](https://doi.org/10.5281/zenodo.14747822), data flow categories, and
  Bloom's taxonomy
- **Context information**: Discipline, target groups, and research object types
- **Technical details**: Git repository links and multilingual text support
  (`MultilingualText`)

Two naming conventions apply: field names are written in `camelCase` (e.g.
`timeRequired`, `dateModified`), and properties holding a list of objects end with the
suffix `LIST` (e.g. `authorLIST`, `learningObjectiveLIST`) so that the expected shape is
immediately visible in the YAML file. The metadata of an OER is maintained in a single
YAML file named `quadriga-metadata.yml` in the root directory of the OER's Git
repository.

See [`examples/quadriga-metadata.yml`](./examples/quadriga-metadata.yml) for a
real-world example (v2.0.0) showing how these elements work together to describe an
educational resource, or [`examples/minimal_metadata.yml`](./examples/minimal_metadata.yml)
for a minimal example following v1.0.0. An XML serialization of the v2.0.0 example is
available as [`examples/quadriga-metadata.xml`](./examples/quadriga-metadata.xml).

### Canonical order of the elements in `quadriga-metadata.yml`

The following order of elements is recommended for v2.0.0 (required fields have an
asterisk after their name):

```
- title*
- authorLIST*
  - (definition of each author)
    - givenName*
    - familyName*
    - orcid
    - affiliation
    - creditLIST
- keywordLIST*
- description*
- tableOfContents*
- disciplineLIST*
- researchObjectTypeLIST*
- targetGroupLIST*
- timeRequired*
- language*
- contributorLIST
  - (definition of each contributor, same structure as authors)
- identifier*
- identifierGit*
- identifierOER*
- prerequisiteLIST
- usedToolLIST
  - (definition for each tool)
    - name*
    - url
- chapterLIST*
  - (definition of each chapter)
    - title*
    - description*
    - url*
    - timeRequired*
    - learningGoal*
    - learningObjectiveLIST*
      - (definition for each learning objective)
        - description*
        - competency*
        - dataFlow*
        - bloomsCategory*
        - assessment
    - supplementalMaterialLIST
      - (definition for each supplemental material)
        - title*
        - url
    - language (only if it differs from the language of the OER)
- dateIssued*
- dateModified*
- version*
- contextOfCreation*
- qualityAssurance*
  - description*
  - date*
- learningResourceType*
- schemaVersion*
- license*
- licenseCode
```

v1.0.0 uses kebab-case field names (`authors`, `learning-objectives`, …), a combined
`license` object with `content`/`code`, and the file name `metadata.yml`; see the
[v1.0.0 documentation](https://quadriga-dk.github.io/quadriga-schema/v1.0.0/schema.html)
and the [migration section](#migrating-from-v100-to-v200) below.

### Diagrams

You can find an approximation of the application profile in the form of UML class diagrams <a href="https://quadriga-dk.github.io/quadriga-schema/diagrams/" target="_blank">here</a>.

To rebuild the diagrams make sure [Docker](https://www.docker.com) (recommended) or [PlantUML](https://plantuml.com) is installed and run `just diagrams`.

## Usage

### Creating Metadata Files

Create a YAML file following the schema structure — `quadriga-metadata.yml` for v2.0.0
(`metadata.yml` in v1.0.0). Start with the real-world example in
[`examples/quadriga-metadata.yml`](./examples/quadriga-metadata.yml) or the minimal
v1.0.0 example in [`examples/minimal_metadata.yml`](./examples/minimal_metadata.yml).

Declaring the schema URL in a comment for the
[yaml-language-server](https://github.com/redhat-developer/yaml-language-server) enables
autocompletion and validation directly in editors like VS Code or Neovim:

```yaml
# yaml-language-server: $schema=https://quadriga-dk.github.io/quadriga-schema/v2.0.0/schema.json
```

The complete author workflow (including the automatic validation in the build process and
the export to JSON-LD, RDF/XML, OERSI and Citation File Format) is described in the
[QUADRIGA-OER-Manual](https://github.com/quadriga-dk/QUADRIGA-OER-Manual).

You can use `latest` in the application profile URL, but in production we recommend picking
a specific version like `v2.0.0`.

### Migrating from v1.0.0 to v2.0.0

Version 2.0.0 renames all fields from kebab-case to camelCase, appends a `LIST` suffix to
properties holding lists of objects, splits `license` into `license`/`licenseCode`, and
replaces `git`/`url` with `identifierGit`/`identifierOER`. The metadata file is now named
`quadriga-metadata.yml`. This repository provides a conversion script that maps a v1.0.0
`metadata.yml` to a v2.0.0-conformant file:

```bash
uv run convert-metadata-v1-to-v2.py -i metadata.yml -o quadriga-metadata.yml
```

The script prints warnings for information that cannot be carried over losslessly (e.g.
v1 `supplemented-by` entries without a URL). Review the converted file afterwards — in
particular add `licenseCode` if the OER contains program code. A field-by-field mapping
table is available in the
[metadata chapter of the QUADRIGA-OER-Manual](https://github.com/quadriga-dk/QUADRIGA-OER-Manual/blob/main/technologie/metadaten.md).

### Vocabulary Mappings (x-mappings)

The QUADRIGA Application Profile uses a custom `x-mappings` extension field to document how
application profile elements (properties or types) map to standard vocabularies. This approach
co-locates crosswalk mappings directly within the application profile definition, making them
machine-readable and version-controlled alongside the application profile itself.

#### Structure

Each application profile element can include an `x-mappings` field that maps to eight
target vocabularies:

```json
{
  "title": {
    "type": "string",
    "description": "Titel der OER",
    "x-mappings": {
      "dc": {
        "relation": "skos:exactMatch",
        "target": "dc:title"
      },
      "dcat": {
        "relation": "skos:exactMatch",
        "target": "dcterms:title"
      },
      "dcterms": {
        "relation": "skos:exactMatch",
        "target": "dcterms:title"
      },
      "hermes": {
        "relation": "skos:exactMatch",
        "target": "dcterms:title"
      },
      "lom": {
        "relation": "skos:exactMatch",
        "target": "1.2 General Title"
      },
      "lrmi": null,
      "modalia": {
        "relation": "skos:exactMatch",
        "target": "dcterms:title"
      },
      "schema": {
        "relation": "skos:broadMatch",
        "target": "schema:name"
      }
    }
  }
}
```

Each vocabulary key holds either `null` (no mapping identified), a single mapping entry,
or an array of mapping entries when an element maps to several terms of the same
vocabulary. Entries may carry a `$comment` documenting mapping decisions. The `target`
supports four formats:

- a prefixed term using a namespace from `@context` (e.g. `dc:title`),
- a full URI (e.g. `https://github.com/tibonto/educor#EducationalResource`),
- a LOM data element path (e.g. `2.3.2 Life Cycle Contribute Entity`), or
- a DOI-qualified reference (e.g. `10.5281/zenodo.8010617 learningObjectives`).

#### Target Vocabularies

- **dc**: [Dublin Core Elements](http://purl.org/dc/elements/1.1/)
- **dcat**: [Data Catalog Vocabulary](http://www.w3.org/ns/dcat#)
- **dcterms**: [DCMI Metadata Terms](http://purl.org/dc/terms/)
- **hermes**: [HERMES OER metadata schema](https://zenodo.org/records/17279619)
- **lom**: [IEEE Learning Object Metadata](https://doi.org/10.1109/IEEESTD.2020.9262118)
- **lrmi**: [Learning Resource Metadata Initiative](http://purl.org/dcx/lrmi-terms/)
- **modalia**: [Modalia ontology](https://purl.org/ontology/modalia#)
- **schema**: [Schema.org](http://schema.org/)

#### SKOS Relation Types

Mappings use [SKOS mapping relations](https://www.w3.org/TR/skos-reference/#mapping)
to indicate semantic relationships:

- `skos:exactMatch`: Properties are semantically equivalent
- `skos:closeMatch`: Properties are closely related but not identical
- `skos:broadMatch`: Target property is broader in meaning
- `skos:narrowMatch`: Target property is narrower in meaning
- `skos:relatedMatch`: Properties are related but not hierarchically

Use `null` when no appropriate mapping was identified for a vocabulary.

#### Mapping Matrix

An interactive mapping matrix showing all application profile elements mapped against the
target vocabularies is available for each application profile version:

- **Latest:**
  [https://quadriga-dk.github.io/quadriga-schema/latest/mapping-matrix.html](https://quadriga-dk.github.io/quadriga-schema/latest/mapping-matrix.html)
- **v1.0.0:**
  [https://quadriga-dk.github.io/quadriga-schema/v1.0.0/mapping-matrix.html](https://quadriga-dk.github.io/quadriga-schema/v1.0.0/mapping-matrix.html)
- **v2.0.0:**
  [https://quadriga-dk.github.io/quadriga-schema/v2.0.0/mapping-matrix.html](https://quadriga-dk.github.io/quadriga-schema/v2.0.0/mapping-matrix.html)

The matrix is color-coded by SKOS relation type (using a colorblind-safe
palette). Each element links to the HTML documentation of the application profile and
each target term to its vocabulary, the value range (Wertebereich) of elements with
controlled vocabularies is shown, and mapping comments are displayed as tooltips.

To build the mapping matrix locally, run `just mapping-matrix` (output will be
in `_build/<version>/mapping-matrix.html`).

#### Meta-Schema

The `x-mappings` structure is validated by
[x-mappings-meta-schema.json](./x-mappings-meta-schema.json), which ensures
consistent mapping documentation across all application profile files.

## Documentation

- **HTML Documentation:**
  [https://quadriga-dk.github.io/quadriga-schema/](https://quadriga-dk.github.io/quadriga-schema/)
- **Latest application profile:**
  [https://quadriga-dk.github.io/quadriga-schema/latest/schema.json](https://quadriga-dk.github.io/quadriga-schema/latest/schema.json)

To build the HTML documentation locally, run `just html` (output will be in
`_build/`).

### Local Development

This project uses [just](https://just.systems) as a command runner. Install it
with `brew install just` (macOS) or see the
[installation docs](https://just.systems/man/en/packages.html) for other
platforms. Run `just --list` to see all available recipes:

```
just validate           # Validate x-mappings in all application profile files
just diagrams           # Build all PlantUML diagrams (auto-detect Docker vs local)
just diagrams docker    # Force Docker for building diagrams
just diagrams list      # List available diagrams
just diagram <name>     # Build a single diagram by name
just html               # Build HTML documentation (validates first)
just mapping-matrix     # Generate mapping matrix HTML for all versions
just build              # Build everything: diagrams + HTML docs + mapping matrix
just serve              # Serve built HTML at http://localhost:8000
just clean              # Clean build artifacts
```

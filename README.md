# QUADRIGA Metadata Schema

[![DOI](https://zenodo.org/badge/1007838017.svg)](https://doi.org/10.5281/zenodo.18184772)

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [QUADRIGA Metadata Schema](#quadriga-metadata-schema)
  - [About This Repository](#about-this-repository)
  - [Schema Structure](#schema-structure)
    - [Canonical order of the elements in `metadata.yml`](#canonical-order-of-the-elements-in-metadatayml)
    - [Diagrams](#diagrams)
  - [Usage](#usage)
    - [Creating Metadata Files](#creating-metadata-files)
    - [Vocabulary Mappings (x-mappings)](#vocabulary-mappings-x-mappings)
      - [Structure](#structure)
      - [Target Vocabularies](#target-vocabularies)
      - [SKOS Relation Types](#skos-relation-types)
      - [Meta-Schema](#meta-schema)
  - [Documentation](#documentation)

<!-- markdown-toc end -->


The QUADRIGA Metadata Schema is a JSON-Schema designed for describing Open
Educational Resources (OER) in German academic contexts. It provides structured
metadata for learning materials, integrating competency frameworks, Bloom's
taxonomy, and multilingual support to enable comprehensive resource description
and discovery. It is used primarily withing QUADRIGA as ground truth within a
Jupyter Book repository and to allow the Navigator to ingest this metadata for
retrieval purposes.

The schema emphasizes semantic web compatibility through [Dublin
Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) and
[Schema.org](https://schema.org/) mappings, while supporting flexible person
representation, learning objectives tracking, and quality assurance workflows
tailored for educational content creation and management.

## About This Repository

This repository contains the complete QUADRIGA schema definition split into
modular JSON files for maintainability. It features a versioning system with a
`latest/` symlink pointing to the current version, automated HTML documentation
generation via GitHub Actions, and deployment to GitHub Pages for easy access
and reference.

**Entry Point:** `schema.json`

**Licensing:** The schema is licensed under CC0 (see `LICENSE-SCHEMA.txt`). Any
code in this repository is licensed under MIT (see `LICENSE-CODE.txt`).

**Archiving:** The schema is archived on Zenodo for long-term preservation and
citable DOI assignment. Zenodo metadata is maintained in `.zenodo.json`.

## Schema Structure

The schema describes educational resources with the following key components:

- **Basic metadata**: Title, description, identifiers, publication dates, and
  versioning
- **Authors and contributors**: Structured person information with
  [ORCID](https://orcid.org/) and [CRediT](https://credit.niso.org) support
- **Content organization**: Chapter-based structure with individual learning
  objectives
- **Competency mapping**: Integration with [QUADRIGA data literacy
  framework](https://doi.org/10.5281/zenodo.14747822), data flow categories, and
  Bloom's taxonomy
- **Context information**: Discipline, target groups, and research object types
- **Technical details**: Git repository links and multilingual text support

See `examples/minimal_metadata.yml` for a complete example showing how these
elements work together to describe an educational resource.

### Canonical order of the elements in `metadata.yml`
The following order of elements is recommended (required fields have an asterisk after their name):

```
- title*
- authors*
  - (definition of each author)
    - famliy-names*
    - given-names*
- keywords
- description*
- table-of-contents*
- discipline*
- research-object-type*
- target-group*
- time-required*
- language*
- contributors*
  - (definition of each contributor)
    - famliy-names*
    - given-names*
- identifier*
- git
- url
- prerequisites
- used-tools
  - (definition for each tool)
    - name
    - url
- chapters*
  - (definition of each chapter)
    - title*
    - description*
    - url
    - time-required*
    - learning-goal*
    - learning-objectives*
      - (definition for each learning-objective)
        - learning-objective*
        - competency*
        - data-flow*
        - blooms-category*
        - assessment
        - jupyter-book-glue-id (only for internal use)
    - supplemented-by
      - (definition for each supplemental material)
        - title*
        - url*
        - note
    - language (only allowed if it overwrites the books language)
- date-issued*
- date-modified*
- version*
- context-of-creation*
- quality-assurance
- learning-resource-type
- schema-version*
- license*
  - content*
  - code
```

### Diagrams

You can find an approximation of the schema in the form of UML class diagrams <a href="https://quadriga-dk.github.io/quadriga-schema/diagrams/" target="_blank">here</a>.

To rebuild the diagrams make sure [PlantUML](https://plantuml.com) is installed and run `./build-diagrams.sh`.

## Usage

### Creating Metadata Files

Create a YAML file following the schema structure. Start with the minimal
example:

```yaml
# yaml-language-server: $schema=https://quadriga-dk.github.io/quadriga-schema/v1.0.0/schema.json
title: Title of the whole book
authors:
  - given-names: test
    family-names: author
    orcid: https://orcid.org/0000-0000-0000-0000 # not necessary but strongly advised
contributors:
  - given-names: Test
    family-names: Mitarbeiter\*in
identifier: DOI of the book as a whole
date-issued: 2025-06-24
date-modified: 2025-10-23
version: 0.1.0
description: Description of the whole book
time-required: PT1H # Duration formatted in ISO8601
table-of-contents: Table of contents of the whole book. Mostly a list of chapter titles formatted in Markdown.
chapters:
  - title: The title of the chapter
    description: A short description of the chapter and its contents.
    url: example.com
    time-required: PT1H # Duration formatted in ISO8601
    learning-goal: Overarching learning goal of the chapter as a whole.
    learning-objectives:
      - learning-objective: one specific learning objective
        competency: Orientierungswissen
        data-flow: übergreifend
        blooms-category: 1 Erinnern
research-object-type:
  - übergreifend
discipline:
  - übergreifend
target-group:
  - Promovierende
context-of-creation: "Die vorliegenden Open Educational Resources wurden durch das Datenkompetenzzentrum QUADRIGA erstellt.\n\nFörderkennzeichen: 16DKZ2034"
language: de
license:
  content: https://creativecommons.org/licenses/by-sa/4.0/
git: https://github.com/quadriga-dk/nonexistant_case_study
schema-version: 1.0.0
```

You can use `latest` in the schema URL, but in production we recommend picking
a specific `schema-version` like `v1.0.0`.

### Vocabulary Mappings (x-mappings)

The QUADRIGA schema uses a custom `x-mappings` extension field to document how
schema elements (properties or types) map to standard vocabularies. This approach
co-locates crosswalk mappings directly within the schema definition, making them
machine-readable and version-controlled alongside the schema itself.

#### Structure

Each schema element can include an `x-mappings` field that maps to seven target
vocabularies:

```json
{
  "title": {
    "type": "string",
    "description": "Titel des Buchs",
    "x-mappings": {
      "dc": {
        "relation": "skos:exactMatch",
        "target": "dc:title"
      },
      "dcat": null,
      "dcterms": {
        "relation": "skos:exactMatch",
        "target": "dcterms:title"
      },
      "hermes": {
        "relation": "skos:exactMatch",
        "target": "hermes:title"
      },
      "lrmi": null,
      "modalia": null,
      "schema": {
        "relation": "skos:exactMatch",
        "target": "schema:name"
      }
    }
  }
}
```

#### Target Vocabularies

- **dc**: [Dublin Core Elements](http://purl.org/dc/elements/1.1/)
- **dcat**: [Data Catalog Vocabulary](http://www.w3.org/ns/dcat#)
- **dcterms**: [DCMI Metadata Terms](http://purl.org/dc/terms/)
- **hermes**: [HERMES OER metadata schema](https://zenodo.org/records/17279619)
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

#### Meta-Schema

The `x-mappings` structure is validated by
[x-mappings-meta-schema.json](./x-mappings-meta-schema.json), which ensures
consistent mapping documentation across all schema files.

## Documentation

- **HTML Documentation:**
  [https://quadriga-dk.github.io/quadriga-schema/](https://quadriga-dk.github.io/quadriga-schema/)
- **Latest Schema:**
  [https://quadriga-dk.github.io/quadriga-schema/latest/schema.json](https://quadriga-dk.github.io/quadriga-schema/latest/schema.json)

To build the HTML documentation locally, run `./build-html.sh` (output will be
in `_build/`).

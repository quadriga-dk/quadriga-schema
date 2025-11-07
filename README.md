# QUADRIGA Metadata Schema

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

## Usage

### Creating Metadata Files

Create a YAML file following the schema structure. Start with the minimal
example:

```yaml
# yaml-language-server: $schema=https://quadriga-dk.github.io/quadriga-schema/v1.0.0/schema.json
schema-version: 1.0.0
title: Title of the whole book
identifier: DOI of the book as a whole
authors:
  - given-names: test
    family-names: author
    orcid: https://orcid.org/0000-0000-0000-0000
contributors:
  - Test Mitarbeiter*in
description: Description of the whole book
table-of-contents: Table of contents of the whole book. Mostly a list of chapter titles formatted in Markdown.
date-modified: 2025-10-23
date-issued: 2025-06-24
version: 0.1.0
language: de
license:
  content: https://creativecommons.org/licenses/by-sa/4.0/
chapters:
  - title: The title of the chapter
    description: A short description of the chapter and its contents.
    learning-goal: Overarching learning goal of the chapter as a whole.
    time-required: PT1H
    learning-objectives:
      - learning-objective: one specific learning objective
        competency: Orientierungswissen
        data-flow: übergreifend
        blooms-category: 1 Erinnern
git: https://github.com/quadriga-dk/quadriga-schema
context-of-creation: "Die vorliegenden Open Educational Resources wurden durch das Datenkompetenzzentrum QUADRIGA erstellt.<br><br>Förderkennzeichen: 16DKZ2034"
time-required: PT1H
discipline:
  - übergreifend
research-object-type:
  - übergreifend
target-group:
  - Promovierende
```

You can use `latest` in the schema URL, but in production we recommend picking
a specific `schema-version` like `v1.0.0`.

### Vocabulary Mappings (x-mappings)

The QUADRIGA schema uses a custom `x-mappings` extension field to document how
each property maps to standard vocabularies. This approach co-locates crosswalk
mappings directly within the schema definition, making them machine-readable
and version-controlled alongside the schema itself.

#### Structure

Each schema property can include an `x-mappings` field that maps to five target
vocabularies:

```json
{
  "title": {
    "type": "string",
    "description": "Titel des Buchs",
    "x-mappings": {
      "dc": {
        "relation": "skos:exactMatch",
        "property": "dc:title"
      },
      "dcterms": {
        "relation": "skos:exactMatch",
        "property": "dcterms:title"
      },
      "lrmi": null,
      "modalia": null,
      "schema": {
        "relation": "skos:exactMatch",
        "property": "schema:name"
      }
    }
  }
}
```

#### Target Vocabularies

- **dc**: [Dublin Core Elements](http://purl.org/dc/elements/1.1/)
- **dcterms**: [DCMI Metadata Terms](http://purl.org/dc/terms/)
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

# QUADRIGA Metadata Schema

The QUADRIGA Metadata Schema is a JSON Schema designed for describing Open Educational Resources (OER) in German academic contexts. It provides structured metadata for learning materials, integrating competency frameworks, Bloom's taxonomy, and multilingual support to enable comprehensive resource description and discovery. It is used primarily withing QUADRIGA as ground truth within a Jupyter Book repository and to allow the Navigator to ingest this metadata for retrieval purposes.

The schema emphasizes semantic web compatibility through Dublin Core and Schema.org mappings, while supporting flexible person representation, learning objectives tracking, and quality assurance workflows tailored for educational content creation and management.

## About This Repository

This repository contains the complete QUADRIGA schema definition split into modular JSON files for maintainability. It features a versioning system with a `latest/` symlink pointing to the current version, automated HTML documentation generation via GitHub Actions, and deployment to GitHub Pages for easy access and reference.

**Entrypoint:** `schema.json`

**Licensing:** The schema is licensed under CC0 (see `LICENSE-SCHEMA.txt`). Any code in this repository is licensed under MIT (see `LICENSE-CODE.txt`).

## Schema Structure

The schema describes educational resources with the following key components:

- **Basic metadata**: Title, description, identifiers, publication dates, and versioning
- **Authors and contributors**: Structured person information with ORCID support
- **Content organization**: Chapter-based structure with individual learning objectives
- **Competency mapping**: Integration with QUADRIGA competency framework, focus areas, data flow categories, and Bloom's taxonomy
- **Context information**: Creation context, duration, discipline, target groups, and research object types
- **Technical details**: Git repository links and multilingual text support

See `examples/minimal_metadata.yml` for a complete example showing how these elements work together to describe an educational resource.

## Documentation

- **HTML Documentation:** [https://quadriga-dk.github.io/quadriga-schema/](https://quadriga-dk.github.io/quadriga-schema/)
- **Latest Schema:** [https://quadriga-dk.github.io/quadriga-schema/latest/schema.json](https://quadriga-dk.github.io/quadriga-schema/latest/schema.json)

## Related Links
- **QUADRIGA Data Literacy Framework (german):** [https://doi.org/10.5281/zenodo.15058057](https://doi.org/10.5281/zenodo.15058057)

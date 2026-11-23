# Development

## Tests

```bash
make test          # unit tests: pytest tests/ -m "not db"
make test-db       # MySQL via compose, then pytest tests/ -m db
```

Mark live-database tests with `@pytest.mark.db` (registered in `pyproject.toml`).

## Documentation

```bash
pip install -e ".[docs]"
make docs          # live preview at http://127.0.0.1:8000
make docs-build    # build into site/
```

The site is built with MkDocs and Material from `docs/` and `mkdocs.yml`. The API reference is generated from the
docstrings (Google style), one page per module. Notebooks in `examples/tutorials/` are copied into the site by
`docs/gen_examples.py` and shown with their saved outputs, not
executed: run them and save before committing.

CI (`.github/workflows/docs.yml`) builds the site on every pull request and publishes it to GitHub Pages on every push
to `main`.

## Changing what a helper writes

Bump the writer version of the ingestion package (`_version.py`) when a helper changes what it writes or what it
hashes; see [Row stamps](guides/provenance.md#row-stamps).

## Examples

Example code under `examples/` is not installed or tested by the package.

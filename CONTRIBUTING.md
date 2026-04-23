# Contributing

Thanks for contributing to the Knowhere Python SDK.

## Development Setup

Requirements:

- Python 3.9+
- `uv`

Clone the repository and install the full development environment:

```bash
uv sync --all-extras
```

## Local Checks

Run these commands before opening a pull request:

```bash
uv run ruff check src/
uv run mypy src/knowhere
uv run pytest -q
```

If you change public behavior, also update the relevant documentation in:

- `README.md`
- `docs/usage.md`
- `examples/`

## Pull Requests

Please keep pull requests focused and easy to review.

Recommended checklist:

1. Add or update tests for behavior changes.
2. Keep public types and examples in sync with the implementation.
3. Document any breaking or user-visible changes in the pull request description.

Maintainers handle versioning and release automation through GitHub Actions.

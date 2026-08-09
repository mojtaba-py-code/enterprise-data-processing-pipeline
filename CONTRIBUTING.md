# Contributing

Thanks for taking a look. This is how the project is developed locally and what
CI expects before a change lands.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run a pipeline from a config file:

```bash
edp run configs/<your-config>.yaml
```

## Before you push

These are exactly the steps CI runs, so run them locally first:

```bash
ruff check src tests
mypy src
pytest -q --cov=pipeline --cov-report=term-missing
```

CI runs the same on Python 3.11 and 3.12.

## Conventions

- **The core never changes for a new source, sink or transform.** Each one is a
  plugin registered with the existing registry and selected by name from YAML.
  A PR that adds an `if source_type == ...` branch to the core will be sent back.
- **A config file is the contract.** New plugin options are validated with
  Pydantic and documented in the README; fail loudly on an unknown key rather
  than silently ignoring it.
- **Stages are pure where they can be.** A transform takes a DataFrame and
  returns one; side effects belong in sinks.
- **Tests.** Add tests with the change; use small in-repo fixtures under
  `data/sample`, not large or external datasets.
- **Commits.** Short imperative subject, a body explaining the *why*.

## Reporting a security problem

Do not open a public issue — see [SECURITY.md](SECURITY.md).

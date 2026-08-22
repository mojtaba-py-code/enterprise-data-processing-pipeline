# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The config path may be given positionally — `edp run configs/pipeline.example.yaml`
  — alongside the existing `-c/--config` option.
- Per-plugin option models. Every connector and transform declares the schema of
  its own `options` block, and loading a config validates each stage against the
  model of the plugin it names, so an unknown key or an unregistered plugin type
  fails before the first row is read.
- A secret scan across every reachable commit, so a credential that was committed
  and later deleted still fails the build.
- `bandit` and `pip-audit` in CI, and the matching README badges.
- `SECURITY.md` and `CONTRIBUTING.md`.
- `.mailmap`, folding the original lowercase author spelling into the current one.

### Changed

- CI fails when test coverage drops below 85%, and re-runs weekly so the security
  jobs see a fresh advisory database instead of whatever was known at the last push.
- Dependency floors raised to the lowest releases `pip-audit` reports clean.
- GitHub Actions are pinned to commit SHAs and the workflow token is scoped to
  read.
- Repository links point at the kebab-case name.

### Removed

- Generated output CSVs are no longer tracked; only the sample input under
  `data/sample` is.

### Fixed

- `pip-audit` no longer fails on the runner's preinstalled `setuptools` instead
  of on this project's own dependencies.
- The licence names the copyright holder in full.

### Security

- The container image runs as an unprivileged user, and CI builds it and asserts
  that it does not run as root.
- Key, certificate and credential filenames are ignored, so they cannot be added
  to a commit by accident.

## [1.0.0] - 2026-07-22

### Added

- First release. An entire ETL flow — ingest, validate, transform, load — is
  described by a single YAML document and run from the command line.
- Plugin registries for connectors (`csv`, `json`, `memory`) and eleven
  declarative transforms; adding one never requires touching the core.
- Schema validation with `fail`, `drop` and `quarantine` error policies, and a
  machine-readable data-quality report.
- Structured text or JSON logging threaded through every stage by a run-scoped
  context.
- The `edp` command line: `run`, `validate`, `plugins`.
- MIT licence, and a GitHub Actions matrix running ruff, mypy and pytest on
  Python 3.11 and 3.12.

[Unreleased]: https://github.com/mojtaba-py-code/enterprise-data-processing-pipeline/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/mojtaba-py-code/enterprise-data-processing-pipeline/releases/tag/v1.0.0

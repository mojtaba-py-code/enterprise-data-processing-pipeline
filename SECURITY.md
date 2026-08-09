# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

Security fixes are applied to `main` and released from there.

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Report it privately through GitHub's
[Report a vulnerability](https://github.com/mojtaba-py-code/enterprise-data-processing-pipeline/security/advisories/new)
form, or by email to **mojtaba.python@gmail.com**.

Include what you can:

- the affected version, tag or commit,
- what the issue is and what an attacker gains from it,
- steps or a minimal proof of concept that reproduces it.

## What to expect

- Acknowledgement within **72 hours**.
- An initial assessment within **7 days**.
- A fix and a published advisory once a patch is ready.
- Credit in the advisory, if you want it.

## Scope

The pipeline is driven by a YAML config and consumes data files it did not
produce. In scope:

- code execution or arbitrary object construction through the pipeline config,
- a path in the config escaping its intended directory when a source or sink
  resolves it,
- SQL injection where a sink or source builds a query from config or data,
- a connection string, password or token reaching a log line or an error message,
- a malformed input file that causes unbounded memory or disk use.

Out of scope:

- Vulnerabilities in third-party dependencies (pandas, PyYAML, Pydantic …) —
  report those upstream; if this project's use of one is what makes it
  exploitable, that *is* in scope.
- Findings that require an attacker to already control the host or the process.

## Notes for operators

- A pipeline config is executable intent. Only run configs you trust, and treat
  the config directory with the same care as source code.
- Configuration is loaded as plain YAML data. Do not extend it with a loader
  that can construct arbitrary Python objects.
- Database credentials belong in the environment, never inside a config file
  that gets committed.

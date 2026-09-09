# Contributing

Bug reports, reproducibility reports, and focused improvements are welcome.
Use [GitHub issues](https://github.com/asguinea/conformal-pathways/issues) for
non-sensitive reports. Include the version or commit, Python/OS versions, the
command, expected behavior, and a minimal example using generated data.
Never attach participant records, restricted datasets, credentials, or local
paths containing personal information. See [security reporting](SECURITY.md).

## Development

```sh
uv sync --locked --extra imaging --extra plots
uv run --locked --extra imaging --extra plots pytest
uv run --locked ruff check .
uv run --locked ruff format --check src tests scripts
uv run --locked mypy --strict scripts/audit_release.py
```

Optional image tests use generated fixtures and seeded random weights. They
do not require real data or a pretrained-weight download. Core-only development
can omit the extras; optional tests then report skips.

Keep changes focused. Explain the behavior change and validation in the pull
request. Add regression tests for corrected behavior and meaningful tests for
new algorithms. Do not substitute tests that merely repeat the implementation.
The maintainer reviews changes before merging; API stability is not promised
for this experimental 0.x project.

## Scientific changes

Read the [claim register](docs/claims.md) and [method](docs/sequential-method.md).
Preserve observation timing, group separation, metric denominators, unavailable
outcomes, and abstentions. Changes to a frozen experiment require a new
configuration and prospective amendment. Preserve earlier evidence and failed
attempts. Do not refresh an old source lock to make new code accept an old
experiment. See [reproduction](docs/reproducing.md).

## Attribution and conduct

Submit only material you have the right to contribute. Intentional contributions
are provided under the project's Apache-2.0 license, subject to its contribution
terms. Identify third-party adaptations and preserve their required notices.
Dataset access never implies permission to upload its contents here.

Treat contributors respectfully, critique work rather than people, and avoid
harassment or disclosure of private information. The maintainer may close or
remove abusive contributions.

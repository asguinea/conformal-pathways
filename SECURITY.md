# Security

Only the current `main` branch and latest 0.4.x release receive fixes. This is
experimental research software, not a clinical system or a sandbox for untrusted
code. Historical benchmark tags are immutable reproduction snapshots; use an
isolated environment for them and review the recorded dependencies.

Report vulnerabilities through
[GitHub private vulnerability reporting](https://github.com/asguinea/conformal-pathways/security/advisories/new).
Include a minimal generated-data example, affected revision, impact, and
reproduction steps. Do not post exploit details, credentials, or participant
data in a public issue. No response-time guarantee is offered.

Treat supplied configurations, model files, NumPy artifacts, archives, and Python
extensions as trusted local inputs. Do not load artifacts from an untrusted
source. Run experiments without credentials and with only the required dataset
access. Real traces and caches can contain sensitive or restricted material;
keep them outside tracked files. The demo needs no external data or credentials.

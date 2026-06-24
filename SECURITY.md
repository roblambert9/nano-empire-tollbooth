# Security Policy

## Reporting a vulnerability

Please report security issues privately. **Do not open a public issue for a
suspected vulnerability.**

- Email: **ops@nano-empire.dev**
- Or use GitHub's private vulnerability reporting:
  [Report a vulnerability](https://github.com/roblambert9/nano-empire-tollbooth/security/advisories/new)

You can expect an acknowledgement within a few business days. Please include
steps to reproduce and the package version (`pip show nano-empire-tollbooth`).

## Supported versions

Only the latest released version on PyPI is supported with security fixes.

## Scope notes

- `nano-empire-tollbooth` runs **locally** and writes a JSONL ledger to disk; it
  does not transmit your data anywhere by default.
- Paper-mode metering performs **no real money movement**. Live settlement
  (`--live`) fails closed until you wire your own payment rail.
- License keys are Ed25519-signed and verified locally; report any signature
  bypass or key-forgery vector through the channel above.

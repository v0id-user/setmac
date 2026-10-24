# Security policy

## Supported versions

Only the latest stable release and the current `main` branch get security fixes.

## Reporting a vulnerability

Please do not open a public issue for a security problem.

- Preferred: use GitHub's private vulnerability reporting on this repository (**Security → Report a vulnerability**).
- Or email **hey@v0id.me** with "setmac security" in the subject.

Include what you found, how to reproduce it, and the impact you expect. You should get a first reply within 7 days. Once a fix ships, the advisory credits you unless you ask otherwise.

## Scope

setmac runs installers and shell commands from its manifest, often with admin rights, so these count as security issues:

- A way to run commands the manifest or profile did not declare.
- The admin password leaking (to logs, disk, the process list, or another process).
- A dotfile being written outside the user's home directory, or over a file it should not touch.
- Secrets being captured into a tracked folder or sent anywhere.
- Release artifacts that are not what the signed source builds.

Running a manifest or profile you chose to trust is not a vulnerability by itself: it is the tool working as designed. Review third party profiles before trusting them.

## Secrets in this repository

CI scans every push and pull request with [gitleaks](https://github.com/gitleaks/gitleaks). Run the same scan locally before you commit with `lefthook install` (see `CONTRIBUTING.md`).

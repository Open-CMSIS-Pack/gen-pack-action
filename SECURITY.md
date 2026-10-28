# Security Policy

## Reporting a Vulnerability

Please report suspected security vulnerabilities privately using
[GitHub private vulnerability reporting](https://github.com/Open-CMSIS-Pack/gen-pack-action/security/advisories/new).
Do not disclose vulnerability details in public issues or pull requests before
coordinating with the maintainers.

Include the following where possible:

- The affected commit SHA or action reference.
- A description of the vulnerability and its potential impact.
- A minimal workflow or other steps to reproduce the issue.
- Relevant runner details, workflow permissions, and prerequisites.
- Any suggested mitigation or fix.

Remove credentials, tokens, and other sensitive data from examples and logs.

## Affected Versions

Please report suspected vulnerabilities in any revision of this action. If
possible, check whether the issue also affects the current `main` branch.
Maintainers will assess affected revisions and discuss remediation through the
private report. This policy does not establish a support or backport schedule
for historical commits.

## Scope and Security Boundaries

This project provides a GitHub composite action for generating documentation and
CMSIS packs, uploading artifacts, updating release metadata, and publishing
documentation to GitHub Pages. The action definition, helper scripts, and
provided workflow templates are relevant to security reports.

The action executes scripts supplied by the calling workflow and can use that
workflow's GitHub token. Review workflow configuration, scripts, and download
URLs as executable build inputs. Use the minimum token permissions required,
and avoid running untrusted pull request code with secrets or write access.

Potential security issues include untrusted data being interpreted as commands,
unintended disclosure of tokens or secrets, and unauthorized modification of
repository contents, release assets, or published documentation. Please explain
the attacker-controlled input and the permissions required to reproduce a report.

## Coordinated Disclosure

Please use the private report to coordinate investigation, remediation, and
public disclosure with the maintainers. Response and remediation times depend
on the issue; this policy makes no fixed response-time commitment.

For ordinary bugs, feature requests, and suggestions to improve this policy,
use the repository's public issues or pull requests. If you are unsure whether
an issue has security implications, report it privately first.

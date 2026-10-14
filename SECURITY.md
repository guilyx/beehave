# Security policy

## Supported versions

While Beehave is at 0.x, only the latest minor release receives security
fixes. Fixes ship as a new patch release of that minor version.

| Version | Supported |
| --- | --- |
| Latest 0.x minor release | Yes |
| Older releases | No |
| Unreleased `main` | Best effort |

Once 1.0 is out, this table will list the supported release lines explicitly.

## Reporting a vulnerability

**Please do not report security problems in public issues, pull requests or
discussions.**

Report them privately through GitHub's private vulnerability reporting:

1. Open the [Security tab](https://github.com/guilyx/beehave/security) of the
   repository.
2. Click **Report a vulnerability**
   ([direct link](https://github.com/guilyx/beehave/security/advisories/new)).
3. Describe the problem. Helpful details:
   - the Beehave version (`beehave --version`) and Python version;
   - a minimal tree file, config file or command that triggers it;
   - what an attacker can achieve, and under which assumptions;
   - any suggested fix.

Only the maintainer can see the report. If you cannot use GitHub's form,
reach out through the contact options on
[github.com/guilyx](https://github.com/guilyx) and we will find a private
channel.

## What happens next

Beehave is maintained by volunteers, so these are targets, not guarantees:

- We acknowledge the report within **7 days**.
- We confirm whether it is a vulnerability, and how severe, within
  **30 days**, and keep you updated as we work on it.
- We prepare the fix in a private fork, publish a patch release, and then
  publish a GitHub Security Advisory (with a CVE where appropriate).
- We credit you in the advisory unless you prefer to stay anonymous.

Please give us a reasonable chance to release a fix before you disclose the
problem publicly. We aim to do so within 90 days of the report.

## Scope

Beehave reads files that may come from other people: BehaviorTree.CPP XML
(and every file it `<include>`s) and `beehave.yaml`. It writes text, Mermaid,
DOT and JSON that may be rendered in a browser. In scope, for example:

- crashes, hangs or excessive memory use caused by a crafted tree or config
  file (Beehave is meant to refuse DTDs and entity tricks outright);
- reading files the user did not ask for;
- output that injects markup or script when a generated Mermaid or DOT
  diagram is rendered;
- problems in our release pipeline or GitHub Actions workflows.

Out of scope: vulnerabilities in BehaviorTree.CPP itself or in the robots that
run the trees, and issues that require an attacker to already control the
machine running Beehave.

## Verifying releases

Every release on PyPI is published from GitHub Actions with trusted
publishing and carries PEP 740 attestations. The files attached to each
GitHub Release are also signed with Sigstore; the `.sigstore.json` bundles
next to them can be checked with:

```sh
python -m pip install sigstore
python -m sigstore verify github \
  --cert-identity "https://github.com/guilyx/beehave/.github/workflows/release.yml@refs/tags/vX.Y.Z" \
  --bundle beehave_bt-X.Y.Z-py3-none-any.whl.sigstore.json \
  beehave_bt-X.Y.Z-py3-none-any.whl
```

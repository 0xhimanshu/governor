# Releasing Governor

This document covers the two public distribution paths for Governor:

1. a GitHub release asset
2. a Claude plugin directory submission

## Build the release package

From the plugin root:

```bash
claude plugin validate .
python3 scripts/build_release.py
```

This creates:

- `dist/governor-v<version>.zip`
- `dist/governor-v<version>.sha256`
- `dist/governor-v<version>-release.json`

The release zip is intentionally lean. It includes the plugin manifest, hooks,
commands, skills, scripts, binaries, assets, install script, and top-level
docs needed for distribution.

## GitHub release

Recommended release assets:

- `governor-v<version>.zip`
- `governor-v<version>.sha256`

Suggested release title:

```text
Governor v<version>
```

Suggested release notes outline:

1. headline improvements
2. benchmark changes
3. install / upgrade note
4. known caveats

## Claude plugin directory submission

Before submitting:

1. make sure the GitHub repo is public
2. make sure `claude plugin validate .` passes
3. decide whether you want to submit the public GitHub repo URL or the release zip

Official submission forms:

- `https://claude.ai/settings/plugins/submit`
- `https://platform.claude.com/plugins/submit`

Current submission requirements from Anthropic:

- public GitHub repo or zip upload
- closed-source plugins are not accepted
- updates pushed to GitHub are mirrored automatically after publication

## Suggested submission copy

### Short description

Governor keeps long Claude Code sessions sharp under quota pressure with
tool-output filtering, context hygiene, telemetry, and drift guardrails.

### Category

`productivity`

### Notes for reviewers

- Claude Code plugin with hooks, commands, skills, and local helper scripts
- no remote MCP dependency required for core behavior
- benchmark artifacts are available in the public repo

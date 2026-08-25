# v12x-skills

[Português](README.md) · **English**

[![Release](https://img.shields.io/github/v/release/V12X/v12x-skills?label=release&color=2ea043)](https://github.com/V12X/v12x-skills/releases/latest)
[![License](https://img.shields.io/github/license/V12X/v12x-skills?color=blue)](LICENSE)

Skills by [V12X](https://github.com/V12X) for [Claude Code](https://claude.com/claude-code).
One repository, several skills, installable together as a plugin marketplace.

> **Heads-up on language.** The skills' guidance — `SKILL.md` and its references — is written in
> **Portuguese**. This README and the [method](METHOD.en.md) are bilingual so the ideas travel;
> the audit playbook itself is not translated yet. Saying so up front is the method applied to
> our own docs: no silent hole.

## Skills

| Skill | What it does |
|---|---|
| **[v12x-scan](skills/v12x-scan)** | In-depth security audit — deterministic tools before reading, adversarial verification of every finding, a report that ends in a publication verdict. Covers the fundamentals, web application (IDOR, SSRF, XSS), backends beyond TS/JS (Python, Go, Ruby, PHP, Java), agentic/LLM apps (prompt injection, MCP), native iOS, multi-tenancy, supply chain/CI, and pre-publication cleanup. Ships `scripts/fase0.sh` (the whole deterministic phase in one command) plus CI and baseline templates. |
| **[v12x-design-audit](skills/v12x-design-audit)** | **Design-system conformance** audit, with the swaps applied. Sweeps screen by screen what is actually painted, compares against your tokens (color by perceptual ΔE, radius/spacing by distance, font by family), and produces the `used value → token` table that drives the swaps. For when the design system was defined **after** the screens existed. Guidance is in Portuguese. |
| **[v12x-agent-audit](skills/v12x-agent-audit)** | **Trust** audit for agents, MCP servers, and skills — before you install a third-party one or publish your own. Extracts the surface (tools, descriptions, permissions, dangerous patterns) without running the server and ends in an install/publish verdict. Covers tool-description poisoning, indirect prompt injection, excessive agency, exfiltration, and provenance/rug pull. Guidance is in Portuguese. |

## Install

> Tested step-by-step, with troubleshooting, in **[INSTALL.md](INSTALL.md)**.

### As a plugin marketplace (recommended)

In Claude Code:

```
/plugin marketplace add V12X/v12x-skills
/plugin install v12x-scan@v12x-skills
```

### Manual

Copy the skill folder into your skills directory:

```bash
git clone https://github.com/V12X/v12x-skills.git
cp -R v12x-skills/skills/v12x-scan ~/.claude/skills/
```

## Use

Once installed, the skill triggers on its own when you ask for an audit, or by name:

```
/v12x-scan audit this repository before I publish it
```

The skill responds in Portuguese.

## Principles

These skills follow the [**v12x Method**](METHOD.en.md) — a security audit in four theses:

1. **Tools before opinion.** What a deterministic scanner finds, it finds better, cheaper, and
   without hallucinating. Critical reading enters where the tool can't reach.
2. **No silent hole.** The report states what was and wasn't covered. The difference between
   "found nothing" and "didn't look" has to be written down.
3. **Refute before reporting.** Every finding survives an explicit refutation attempt. One false
   positive destroys trust in the whole report.
4. **Verdict, not score.** No 0-to-100 grade: a count by severity and a binary decision to
   publish.

The full manifesto, with the reasoning and a counterexample for each thesis, is in
[METHOD.en.md](METHOD.en.md).

## Changelog

Per-version changes in [CHANGELOG.md](CHANGELOG.md). Current version is
[v1.2.0](https://github.com/V12X/v12x-skills/releases/tag/v1.2.0).

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Before shipping any new skill, run `v12x-scan` on it: `.gitignore` covering secrets, a clean
history scan, no machine paths or internal names leaked. The tool audits its own tools. Style,
versioning, and release details in [CONTRIBUTING.md](CONTRIBUTING.md) (Portuguese).

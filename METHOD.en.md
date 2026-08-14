# The v12x Method

*A security audit you can trust enough to act on.*

[Português](METHOD.md) · **English**

In the age of AI-generated code, almost everyone audits and almost no one trusts the result.
Security audits fail in two ways, and both are fatal in opposite directions: either they
**produce noise** — false positives that train the reader to ignore the whole report — or they
**produce false confidence** — a nice score painted over a hole.

The v12x Method is four rules that produce the opposite: an audit that is **reproducible, honest
about what it didn't see, with every finding verified, and ending in a verdict** — not a metric.
The test of the method is simple: *can you decide whether to publish based on it?*

It is a method, not a tool. Anyone can follow it with open-source scanners and reporting
discipline. [`v12x-scan`](README.en.md) is the reference implementation.

---

## Thesis 1 — Tools before opinion

What a deterministic scanner finds, it finds **better, cheaper, and without hallucinating.**
Secrets, vulnerable dependencies, dangerous patterns — that's a tool's job, and the tool wins
every time. Critical reading — human or AI — is expensive and fallible, so it is reserved for
where the tool **can't reach**: object-level authorization, tenant isolation, business logic.
Spending judgment where a `grep` would do is waste; trusting judgment where only it works is the
value.

> **Counterexample.** Asking a model "find the secrets in this repo" and trusting the answer. It
> will miss the git-ignored `.env` — which is exactly where the real key lives — and invent a
> secret in an `example.com`. `gitleaks` over the history does neither.

## Thesis 2 — No silent hole

*"Found nothing"* and *"didn't look"* are different sentences, and a bad report merges them. The
method requires a **coverage map**: every audit states what was left out — a missing tool, a
skipped directory, a category that doesn't apply, a language not covered. A declared hole is
manageable: the reader knows where they still need to look. A silent hole is what sinks you,
because it disguises itself as coverage.

> **Counterexample.** A report that claims *"no dependency vulnerabilities"* when the dependency
> scanner wasn't even installed. The sentence is technically true and completely misleading — it
> conveys a confidence that was never earned.

## Thesis 3 — Refute before reporting

Reading-based audits have a high false-positive rate, and **a single false positive destroys
trust in the whole report** — the reader learns to discard everything. So no finding enters the
report without surviving an **explicit refutation attempt**: is there validation in an earlier
layer? middleware that already blocks it? a database policy that already covers it? If the
finding dies under that test, good — it shouldn't have been there. Five findings that survive
are worth more than thirty candidates, twenty of which are noise.

> **Counterexample.** Reporting a `dangerouslySetInnerHTML` as XSS without checking that the
> content is a constant written in the code itself. One false positive like that, and the
> developer discards the other twenty-nine findings — including the one that was real.

## Thesis 4 — Verdict, not score

Never reduce the security of a codebase to a number from 0 to 100, nor to a "Pass/Fail" per
category. The score **isn't reproducible** (the same codebase audited twice yields different
scores), **gives false confidence** ("87, good to publish"), and **hides severity** (nineteen
good checks and one exposed credential still score high — which is exactly the dangerous case).
The industry scores **each vulnerability** with a defined rubric — that's what CVSS does — never
a whole codebase holistically. The correct substitute is a **count by severity + a binary
publication verdict**.

> **Counterexample.** *"Security: 92/100 ✅"* on a repository that ships the Supabase
> `service_role` key embedded in the client bundle. One credential is enough for total
> compromise; no arithmetic average expresses that. The correct verdict is one word: **do not
> publish.**

---

## An audit is a cycle, not an event

A one-off audit leaves nothing "hole-proof" — the code changes the next day. What comes close is
closing the cycle:

1. **Persist the report** and **diff against the previous one.** A finding that came back is a
   regression, and a regression goes up a severity level.
2. **Every fix becomes a permanent check.** A fixed "token in logs" is born as a CI test that
   fails if the pattern returns. A finding that only lives in the report comes back.
3. **Re-audit after fixing.** Security fixes introduce regressions with irritating frequency.

If none of this runs on its own, everything depends on someone remembering — and that dependency
**is a finding in itself**.

---

## Reference implementation

[`v12x-scan`](README.en.md) applies the method as a [Claude
Code](https://claude.com/claude-code) skill: deterministic phase first, layer-by-layer analysis,
adversarial verification, severity by consequence, and a report with a coverage map and a
verdict. But the method doesn't depend on it. To adopt it without the tool, the minimum is:

- deterministic scanners first (secrets in the history **and** the working tree, dependencies,
  static patterns), with every absence recorded as not covered;
- reading reserved for authorization and isolation;
- explicit refutation of each finding before reporting;
- a report that ends in a count by severity + a verdict, never a score.

## How to cite

> v12x Method — a security audit in four theses. https://github.com/V12X/v12x-skills

A living document, under the [MIT](LICENSE) license. Well-reasoned disagreement makes the method
better — open an issue.

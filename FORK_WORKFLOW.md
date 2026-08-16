# Fork Workflow

This repository is a personal fork of [valentinfrlch/ha-llmvision](https://github.com/valentinfrlch/ha-llmvision). It exists to carry local fixes and improvements that are not (or not yet) addressed upstream, while staying easy to resynchronize with upstream. The companion card fork is [raouldekezel/llmvision-card](https://github.com/raouldekezel/llmvision-card), run under the same workflow.

## Branch model

| Branch | Role | Rules |
|--------|------|-------|
| `main` | Pristine mirror of upstream `main` | Never commit here directly. Updated exclusively by syncing from upstream. |
| `deploy` | `main` + local pull requests | The branch actually deployed at home. All local work lands here through pull requests. |

Rationale: keeping `main` strictly identical to upstream makes synchronization trivial (fast-forward only, no conflicts on `main` itself) and provides a clean base both for comparing local changes (`main...deploy`) and for preparing upstream contributions.

`deploy` is the repository's default branch for pull-request ergonomics: new PRs target it by default, instead of GitHub proposing the upstream repository as base. The default branch is irrelevant to how HACS installs this fork — see **Distribution (HACS)** below: once releases exist, HACS prefers them over any branch.

## Development process

The process is the one proven on [NavimowHA](https://github.com/raouldekezel/NavimowHA) and [dolphin-robot](https://github.com/raouldekezel/dolphin-robot).

**Language policy:** all repository communication — issues, pull requests, commit messages, and documentation — is written in English.

### Issues

- **Every change starts as an issue**, systematically — bug fix, feature, hardening, chore or investigation alike. Issues carry a typed identifier in the title, numbered per family and local to this repository: `BUG-NN`, `HARD-NN`, `FEAT-NN`, `CHORE-NN`, `SPIKE-NN`.
- **The issue body is the normative source of truth.** Settled design, root cause, discarded alternatives and arbitrated decisions are folded into the body *in place*, with a dated edit trailer. Comments carry only dated session reports and reviews — never normative additions stacked over an outdated body.
- **An issue is closed only by the operator, and only after on-site validation** on the live Home Assistant instance. A merge never closes an issue. If validation fails or reveals a new pathology, the issue reopens or a new `BUG` is filed (the BUG-17 → BUG-19 chain on NavimowHA is the canonical example).

### Branches, pull requests, merges

- Work branches are named `patches/<id>-<slug>` (e.g. `patches/bug-01-timeline-ordering`) and fork off `deploy`.
- One pull request per issue, targeting `deploy` **in this fork**. Double-check the base repository and branch when opening the PR: GitHub tends to preselect the upstream repository.
- Reference issues with `refs #NN` — never `Closes`: closing is an operator act tied to on-site validation, and with `deploy` as the default branch a merged closing keyword would actually auto-close the issue, so the guard is functional, not stylistic.
- Review verdicts are posted as PR comments. Merge happens only on the operator's explicit "ok merge". Work PRs are **squash-merged** — squash is the only merge method enabled on this repository.
- Each deployed, on-site-validated state is published as a **GitHub pre-release** tagged `v<upstream-version>-raoul.N`, with generated notes; a release bundles one or two issues, validated on site before their issues close. See **Distribution (HACS)** below.

### Diagnostics

Field evidence is captured in **diag sessions** under `docs/diag/YYYY-MM-DD_<id>_<topic>/`, each delivered as its own docs-only PR. Structure, evidence formats, PII redaction rules and the drift-proof index are specified in [docs/diag/README.md](docs/diag/README.md) and enforced by `scripts/check_diag_index.py` via the **Check diag index** workflow. Sessions are immutable once merged; later sessions supersede rather than rewrite.

### Tests

- The pytest suite (upstream `tests.yaml`) is the PR gate; the suite count is tracked from review to review.
- **Tests are black-box**: they exercise public behavior and never read internal fields or implementation details (white-box reads are out of scope by rule).
- Regression tests are pinned and named after their issue id. Pinned assertions are never edited or weakened without an explicit, reviewed justification — a pin whose behavior inverts by design is rewritten, with the inversion argued in the PR.
- A test built on mocked scheduling must prove that the asserted path actually executed; a green that never ran the path is a defect, not a pass.

## Distribution (HACS)

HACS reads `/releases`, not `/tags`: a bare git tag is invisible to it and carries no changelog. This fork is therefore distributed as **GitHub pre-releases**:

- Tag grammar: `v<upstream-version>-raoul.N` — base = the upstream version `deploy` currently tracks (see `custom_components/llmvision/manifest.json`), `N` monotonic per upstream base. The `-raoul.N` semver segment marks the release as a pre-release, so HACS must have **"show beta versions"** enabled for this repository.
- Publication: `git push origin <tag>` then `gh release create v<base>-raoul.N --prerelease --generate-notes --target deploy`. `hacs.json` sets no `zip_release`, so HACS downloads the tagged tree directly — no artifact to attach.
- `manifest.json` keeps the **upstream** version (operator-arbitrated): no per-release bump, which would permanently diverge a file upstream touches at every release. HACS shows `<base>-raoul.N` (from the tag); the HA integration page shows the upstream base.
- Cut-over note: publishing the **first** release flips HACS from tracking `deploy` HEAD to installing releases only. Intended (pinning) — cut releases from a validated `deploy` only.

## Day-to-day work

1. Create a feature branch from `deploy` (e.g. `patches/bug-01-timeline-ordering`).
2. Open a pull request targeting `deploy` **in this fork**. Double-check the base repository and branch when opening the PR: GitHub tends to preselect the upstream repository.
3. Review and iterate; merge only on the owner's explicit approval ("ok merge").

## Syncing with upstream

1. Update `main` from upstream: use the **Sync fork** button while on the `main` branch page, or `gh repo sync raouldekezel/ha-llmvision -b main`.
2. Merge `main` into `deploy` **as a local merge pushed directly to `deploy`** — never through a pull request. Squash is the only PR merge method enabled here, and squashing a sync PR would collapse the upstream commits into a single synthetic commit: `deploy` would no longer contain upstream's commit objects, and every subsequent sync would re-conflict on history already integrated. A true merge commit pushed by hand is unaffected — the merge-method restriction only governs the PR merge buttons.

   ```
   git fetch origin
   git checkout deploy
   git merge origin/main
   git push origin deploy
   ```

3. During the merge, resolve conflicts in favor of preserving local changes — unless upstream has properly fixed the underlying issue, in which case drop the now-redundant local patch instead of keeping both variants.

## Contributing back upstream

When a local fix is worth proposing upstream, create a dedicated branch **from `main`** (not from `deploy`) and cherry-pick only the relevant commits onto it, so the upstream pull request contains nothing but the intended change.

## Continuous integration

GitHub disables Actions by default on newly created forks; they must be enabled once from the **Actions** tab before anything runs. The workflows inherited from upstream then trigger on pushes and pull requests:

- `tests.yaml` — unit tests with coverage; this is the meaningful signal for local PRs.
- `validate.yaml` — Hassfest validation plus HACS validation. The HACS jobs check repository metadata (description, topics, issues enabled) that forks do not inherit from upstream.
- `stale.yml` — scheduled issue housekeeping; scheduled workflows are disabled on forks by default, and this one is irrelevant to a personal fork.
- `check-diag-index.yaml` — the one fork-owned addition (on `deploy`), path-filtered to `docs/diag/**`; enforces the diag index and never touches upstream-inherited files.

Policy on this fork: workflow files inherited from upstream are deliberately kept identical to upstream (no local edits) so that syncing never conflicts on them. Instead, the repository metadata the HACS jobs depend on is maintained manually in the repository settings — issues enabled, upstream topics copied — so those jobs stay green.

## Note on this file

`FORK_WORKFLOW.md`, the diag scaffolding and this process section exist only on `deploy` (and branches derived from it), keeping `main` byte-identical to upstream.

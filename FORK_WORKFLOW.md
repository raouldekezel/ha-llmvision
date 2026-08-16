# Fork Workflow

This repository is a personal fork of [valentinfrlch/ha-llmvision](https://github.com/valentinfrlch/ha-llmvision). It exists to carry local fixes and improvements that are not (or not yet) addressed upstream, while staying easy to resynchronize with upstream.

## Branch model

| Branch | Role | Rules |
|--------|------|-------|
| `main` | Pristine mirror of upstream `main` | Never commit here directly. Updated exclusively by syncing from upstream. |
| `deploy` | `main` + local pull requests | The branch actually deployed at home. All local work lands here through pull requests. |

Rationale: keeping `main` strictly identical to upstream makes synchronization trivial (fast-forward only, no conflicts on `main` itself) and provides a clean base both for comparing local changes (`main...deploy`) and for preparing upstream contributions.

Making `deploy` the repository's default branch is recommended: new pull requests then target it by default (instead of GitHub proposing the upstream repository as base), and HACS — which installs from the default branch when a fork has no releases — picks up the deployed version directly.

## Day-to-day work

1. Create a feature branch from `deploy` (e.g. `fix/timeline-ordering`).
2. Open a pull request targeting `deploy` **in this fork**. Double-check the base repository and branch when opening the PR: GitHub tends to preselect the upstream repository.
3. Review and iterate; merge only on the owner's explicit approval ("ok merge").

## Syncing with upstream

1. Update `main` from upstream: use the **Sync fork** button while on the `main` branch page, or `gh repo sync raouldekezel/ha-llmvision -b main`.
2. Merge `main` into `deploy` (via a PR from `main` to `deploy`, or a local merge pushed to `deploy`).
3. During the merge, resolve conflicts in favor of preserving local changes — unless upstream has properly fixed the underlying issue, in which case drop the now-redundant local patch instead of keeping both variants.

## Contributing back upstream

When a local fix is worth proposing upstream, create a dedicated branch **from `main`** (not from `deploy`) and cherry-pick only the relevant commits onto it, so the upstream pull request contains nothing but the intended change.

## Continuous integration

GitHub disables Actions by default on newly created forks; they must be enabled once from the **Actions** tab before anything runs. The workflows inherited from upstream then trigger on pushes and pull requests:

- `tests.yaml` — unit tests with coverage; this is the meaningful signal for local PRs.
- `validate.yaml` — Hassfest validation plus HACS validation. The HACS jobs check repository metadata (description, topics, issues enabled) that forks do not inherit from upstream.
- `stale.yml` — scheduled issue housekeeping; scheduled workflows are disabled on forks by default, and this one is irrelevant to a personal fork.

Policy on this fork: workflow files are deliberately kept identical to upstream (no local edits) so that syncing never conflicts on them. Instead, the repository metadata the HACS jobs depend on is maintained manually in the repository settings — issues enabled, upstream topics copied — so those jobs stay green.

## Note on this file

`FORK_WORKFLOW.md` exists only on `deploy` (and branches derived from it), keeping `main` byte-identical to upstream.

# Git Workflow, Release & Versioning Policy

## 1. Branching Strategy & Merge Flow

* **Main Branch (`main`):** Represents production-stable code. Never commit directly to `main`.
* **Release Branches (`release/vX.Y.Z` or `release/X.Y.Z`):** Intermediate target branches for preparing incoming versions.
* **Feature & Working Branches (`feature/*`, `fix/*`, etc.):** All active development must originate from and pull-request (PR) directly into the **latest active release branch**.
* **Flow:** `feature/*` ➔ `release/vX.Y.Z` ➔ `main`
* **Strict Separation of Operations:** Merging a feature branch into a release branch and merging a release branch into `main` **must never occur in the same task, job, or automated execution**.
* A feature merge only updates the staging/release branch.
* Merging a release branch into `main` is a separate, dedicated step that **requires explicit operator instruction and review**.

### Release Branch Freeze Policy

* **Once a release branch has been tagged or superseded by a newer release branch, it is frozen.** No further commits may be merged into a frozen release branch.
* **Creating a new release branch:** When a new release branch (e.g., `release/v0.1.0`) is created, the previous release branch (e.g., `release/v0.0.1`) must be frozen immediately. Any in-flight feature branches that were targeting the old release must be retargeted to the new one.
* **Port-forward:** When creating a new release branch from an existing one, all commits from the old branch (up to the freeze point) are carried forward. The old branch is reset to its last valid state before the version bump.
* **No commits to frozen branches:** An agent must never commit, merge, or push to a frozen release branch. If a fix is needed for an older release, a hotfix branch (`fix/*`) should be created from the frozen release tag, not from the frozen branch itself.


## 2. Commit & Push Granularity Workflow

To maximize tracking visibility, improve code review legibility, and make git history easily bisectable:

* **Atomic Commits:** Files and discrete changes should be committed and pushed on their own whenever possible. Avoid large "kitchen sink" commits that bundle unrelated files.
* **Tightly Coupled File Grouping:** Files may be grouped into a single commit **only** when they are directly interdependent (e.g., a component file and its dedicated unit test, or an API route and its updated interface type definition).
* **Incremental Pushing:** Push commits to the remote branch frequently as logical units are completed rather than waiting until the end of a long task.
* **Conventional Commit Format:** All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```text
<type>(<optional scope>): <short summary>

[optional body]

[optional footer(s)]

```

### Allowed Types & Version Mapping

* **`feat`** ➔ Triggers a **Minor ($Y$)** release increment (e.g., `feat(auth): add OAuth2 login support`).
* **`fix`** ➔ Triggers a **Sub-release ($Z$)** release increment (e.g., `fix(api): handle null response body`).
* **`perf`**, **`refactor`**, **`docs`**, **`style`**, **`test`**, **`chore`**, **`ci`**, **`build`** ➔ Non-versioned patch / maintenance changes.
* **`BREAKING CHANGE:` or `!` after type** ➔ Triggers a **Major ($X$)** release increment (e.g., `feat(db)!: drop legacy v1 schema support`).

---

## 3. Version Tagging Format (`X.Y.Z`)

All version tags must strictly adhere to the `X.Y.Z` semantic format:

* **`X` (Major):** Breaking changes, major feature overhauls, or architectural updates.
* **`Y` (Minor):** New backwards-compatible features or significant enhancements.
* **`Z` (Sub-release / Patch):** Bug fixes, patch updates, minor refactoring, or hotfixes.

> **Example:** `v1.2.0`, `v2.0.1`

---

## 4. Tagging & Progression Protocol

* **Strict Operator Control:** Never create, increment, or push a Git tag automatically or during routine task completion.
* **Explicit Command Required:** A new tag or version increment must **only** be created when the operator explicitly requests it (e.g., *"Bump version to 1.1.0 and tag it"*).
* **Isolated Release Execution:** An operator must explicitly command the merge of `release/vX.Y.Z` into `main` as an independent action. An agent must never propose or execute a `release` ➔ `main` merge immediately following a `feature` ➔ `release` merge within the same job.
* **Tag Availability Check:** Before creating a tag, inspect existing tags (`git tag -l`) to ensure the tag does not already exist and follows the correct sequence.
* **Main Release:** Tags are created on `main` **only after** the corresponding `release/*` branch has successfully merged into `main`.

---

## 5. Native PreToolUse Hook (`.clinerules/hooks/PreToolUse`)

To programmatically enforce these guardrails inside VS Code, a `PreToolUse` hook script intercepts commands before execution.

---

## 6. Pull Request (PR) Standard

When preparing a PR, ensure the description strictly follows this template:

```markdown
## Overview
- **Target Branch:** `release/vX.Y.Z` (or `main` if releasing a release branch)
- **Source Branch:** `feature/...` / `fix/...` / `release/...`
- **Type of Change:**
  - [ ] Major (X) - Breaking change (`feat!`, `fix!`, or `BREAKING CHANGE`)
  - [ ] Minor (Y) - New feature (`feat`)
  - [ ] Sub-release (Z) - Bug fix / patch (`fix`)

## Summary of Changes
- Briefly state the high-level objective of this PR.
- List key updates, modified components, or newly introduced capabilities.

## Tests
- [ ] Unit / Integration tests added or updated.
- [ ] Manual test verification completed.
- **Testing Steps:**
  1. Step-by-step description of how to verify these changes.
  2. Edge cases or scenario checks tested.

## Release & Versioning Check
- [ ] Commit messages conform to Conventional Commits and atomic/coupled principles.
- [ ] Merge flow is isolated (Feature ➔ Release PR is separate from Release ➔ Main PR).
- [ ] Target branch matches the current branch hierarchy (`feature/*` ➔ `release/vX.Y.Z` ➔ `main`).
- [ ] Explicit operator approval obtained before tagging or merging to `main`.
- [ ] Tag proposed / created: `vX.Y.Z` (if applicable).

```
# Acme technical-screen demo runbook

## 1. What this is

**acme-core** is a private copy of NetworkX used as the stand-in for Acme's graph library. Acme, Pat, Maya, and Priya are fictional. The problem under demo is slow new-engineer onboarding and inconsistent code quality when conventions live only in heads and docs.

## 2. Components and where each lives

| Piece | Path / invocation |
| --- | --- |
| Always-loaded agent instructions | `AGENTS.md` |
| Library conventions rule | `.cursor/rules/library-conventions.mdc` (loads for `networkx/**`) |
| Deprecation skill | `.cursor/skills/acme-deprecate-function/SKILL.md` (invoke as `/acme-deprecate-function`) |
| Convention guard + spec | `tools/acme_guard.py`, `tools/tests/test_acme_guard.py` (14 tests) |
| Hooks | `.cursor/hooks.json` with `.cursor/hooks/deny_upstream.py` and `deny_secrets.py` |
| CI | `.github/workflows/acme-ci.yml` — guard tests, guard, full suite on every PR and every push to `main` |
| Staging deploy | `.github/workflows/deploy-staging.yml` — mock deploy behind the staging environment's required reviewers |
| Ownership | `CODEOWNERS` |

## 3. Controls

**Advice:** `AGENTS.md`, the library-conventions rule, and the deprecate-function skill.

**Deterministic checks:** `acme_guard.py`, its test suite, and `acme-ci`.

**Enforced boundaries:**
- Branch protection on `main`: 1 approval, code owners, stale-review dismissal, last-push approval, required check `check`, admins enforced.
- Staging environment: required reviewers `rohan-c0de` and `acme-qa-bot`; self-review prevented.
- The two Cursor hooks above; the `upstream` remote's push URL set to `push-blocked.invalid`.
- Cursor Run Mode **Allowlist (with Sandbox)** with an empty allowlist; Privacy Mode on.

**Human judgment:** plan approval in Cursor, Grok Bot approval cards, and the release (staging) approval.

## 4. Identities

- **rohan-c0de** — engineer, tech lead, and release approver.
- **acme-qa-bot** — GitHub service account the Grok Bot acts as, authenticated on the Bot's computer via a 30-day classic token with the `repo` scope, held in the Bot's secrets.
- A PR author can never approve their own PR.

## 5. Setup from scratch

```bash
git clone <this-repo>
cd acme-core
python -m venv .venv
source .venv/bin/activate
pip install -e '.[default,test]'
python -m pytest tools/tests -q   # expect 14 passed
python tools/acme_guard.py        # expect 0 violations
```

## 6. The 20-minute demo script

1. Show baseline: `acme/baseline-before.md`.
2. Open issue **#7** (Pat's request plus agent-drafted triage).
3. Create a new branch.
4. Enter Plan mode with `/acme-deprecate-function` and the ticket; answer the in-function-callers question with **leave them**.
5. Build; verify with the guard (expect **1 Acme-era deprecation, 0 violations**), the full suite, and `git diff --stat` (six files).
6. Push and open a PR with label `type: API` and body `Closes #7`.
7. Wait for CI (~2.5 minutes).
8. In Grok Bot: ask for PR status → ask it to approve (approval card) → ask it to merge (approval card).
9. Approve the staging deployment in GitHub Actions; show the `MOCK DEPLOY` log line.

## 7. Failure demonstration

After the build, temporarily delete the added `filterwarnings` line from `networkx/conftest.py` and run the guard — expect a `[deprecation-touchpoints]` violation naming `filterwarnings`. Restore with `git checkout networkx/conftest.py` only if nothing else in that file is pending; otherwise re-add the line.

## 8. Reset between runs

- If the live PR was merged: revert with a PR (`git revert <sha>` on a branch → bot approval → merge).
- If not merged: close the PR and delete its branch.
- On `main`, confirm `python tools/acme_guard.py` reports **0 Acme-era deprecations**.
- Rehearsal PR **#8** can be reopened as a fallback if the live run fails.

## 9. What is mocked, simulated, or limited

- Deploy target prints only (`MOCK DEPLOY`).
- Company and people are fictional; the tech-lead role is played by the same person as the engineer.
- Bot token is a classic PAT with full `repo` scope because fine-grained tokens cannot target another user's repository.
- Hooks and Run Modes apply only to local agents, not Cursor cloud agents.
- The code-owner rule has not yet been exercised against a bot-authored change to a protected path.
- The Cursor API, Bugbot, and Multitask were deliberately not used.

## 10. Supporting tools disclosure

The guard's test suite and the original ticket were drafted with Claude as a supporting tool and validated against planted faults. All other files were built by Cursor from prompts recorded in the author's runbook.

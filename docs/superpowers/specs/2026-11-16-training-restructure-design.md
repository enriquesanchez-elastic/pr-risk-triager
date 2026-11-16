# Evals workshop restructure: repo branches and deck v2

## Intent and why

The workshop teaches evals on `pr-risk-triager`. A review as a participant found that Lab A is invisible:
a fresh clone lands on `main`, which has no `evals/` folder. The Lab A files live on the `solution`
branch and `GUIDE.md` pulls them with `git checkout origin/solution -- ...`. The deck never shows those
commands, never links the guide, and its A1-A6 slide is a menu of titles with no commands or expected
output. The deck and `main` also describe two different Lab Bs (deck: Python SDK on the unmerged
`lab-b-python` branch; `main`: `@kbn/evals`, verified end to end).

Goal: a participant who has only the deck and the repo URL can finish both labs without guessing.

## Goals

- One Lab B: `@kbn/evals` in a Kibana checkout. The Python SDK variant is dropped.
- The repo explains itself: a branch map in `README.md`, one guide per lab, on the branch the lab uses.
- Deck v2 is a new copy (the published deck is left untouched), with one slide per Lab A step showing
  command, files, expected output and a question, and with the repo/branch map shown before Lab A.
- All numbers and times agree across deck, guide and cover.

## Non-goals

- No change to the tool code (`src/triager`), tests, or evaluator logic.
- No new eval content, models, or datasets.
- No step-per-branch scheme and no helper script.
- Golden-cluster and security-weekly-run material is not rewritten; it moves to an appendix.

## Anti-goals (failure even if it "works")

- A participant must never need the speaker notes to know what to type.
- Slides must not contradict the guide (commands, ports, times, scores).
- Do not delete or force-push anything without the owner saying so.

## Approaches considered

- **A. One branch per lab (chosen).** `main`, `lab-a`, `lab-b`. Low maintenance, fixes merge across 3 branches.
- B. One branch per step (about 10 cumulative branches). Exact catch-up, but every fix replays up the chain.
- C. Keep one `solution` branch, fix only docs and slides. Least work, but the pull-from-another-branch
  ceremony stays invisible.

## Design

### Repo

| Branch | Contents | Role |
| --- | --- | --- |
| `main` | tool, 8 unit tests, CI, `README.md` with a branch map, `GUIDE.md` as a short index (timing, setup, links) | Clone target. Starting point and Lab A step A1 |
| `lab-a` | `main` plus `LAB-A.md` and the full `evals/` folder and `evals.yml` workflow | Lab A. Participants `git checkout lab-a` and read, run and change |
| `lab-b` | `main` plus `LAB-B.md` and `kbn-evals/` | Lab B. Files are copied into a Kibana checkout |

- `lab-a` is renamed from `solution`. `LAB-A.md` is the Lab A section of today's `GUIDE.md`, rewritten for
  "files are already here": each step says which file to open, what to run, what you should see.
- Participants do the exact work the deck shows. The one thing they write is a new dataset case in A2.
  Recovery if they break something: `git checkout origin/lab-a -- evals/`.
- `lab-b` carries `LAB-B.md` (today's Lab B section, including the verified gotchas and the EDOT/Scout
  port fix) next to the spec and config.
- `lab-b-python` is obsolete (Python SDK Lab B). It is not deleted by this work; the owner decides.
- `kbn-evals/` stays on `main` as well, so `main` alone is enough for a facilitator demo.
  (Call: duplicates a folder across branches; accepted so nobody needs a branch switch for the demo.)

### Deck v2 outline (new artifact, copy of the current deck)

1. Cover, why, tool (kept; fix the time claim)
2. Anatomy of an eval (kept)
3. **Repo map** (new): branches `main` / `lab-a` / `lab-b`, what each holds, which lab uses which
4. Plan: Part 1 Lab A, Part 2 Kibana intro (short), Part 3 Lab B; no Lab C
5. Lab A divider, then **A1 to A6, one slide each**: command in mono, files touched, expected output, one question
6. Keep "errors are not equal", evaluators, results slides, Lab A done
7. Kibana intro: shrink to where evals live, how a run works (about 5 minutes). Golden cluster, UI tabs,
   run options and the security weekly run move to an appendix after the takeaways
8. Lab B divider, **B1 to B4, one slide each** from the verified `@kbn/evals` guide (smoke test, spec anatomy,
   run two models, compare in UI), plus a gotchas slide
9. Lab B results (replace the Python-SDK example data with the verified comparison), takeaways, prep
   (fix: `uv add --dev pydantic-evals`, `git checkout lab-a`, Kibana bootstrap), appendix

Times: derived from the guide (Lab A 18, Lab B 7 or as verified), with the cover total computed from them.

## Constraints

- Deck is a Slides artifact (1920x1080, inline styles, Space Grotesk, Inter and JetBrains Mono, the current palette).
- Speaker notes stay in plain text, 4,000 characters at most.
- Lab B needs a Kibana checkout with `pnpm kbn bootstrap`; the guide's 7-minute figure assumes it is
  already done before the session.

## Open items left to the builder

- Exact wording of `LAB-A.md` and `LAB-B.md` (derive from the current `GUIDE.md`; do not change commands).
- Slide visual layout, following the existing deck style.
- Whether `GUIDE.md` on `main` shrinks to an index or is removed in favour of the README (my call: keep as index).

## Facts the builder needs (from the repo today)

- `origin/solution` = `main` + `evals/` (5 files) + `.github/workflows/evals.yml` + a README section +
  `pydantic-evals` in `pyproject.toml`/`uv.lock`. `GUIDE.md` is identical on both. It has no Python-SDK Lab B files.
  Main is merged into it regularly. So `lab-a` is a plain branch from `origin/solution`, no cleanup.
- `origin/lab-b-python` is ahead of `solution` (adds `evals/kibana_run.py`, a different `GUIDE.md`,
  `kibana` dependency group). Obsolete under this design.
- The verified numbers live in `GUIDE.md`: A4/A6 scores per model, Lab B ran 2 passed in about 3.6 min against
  two models plus a judge on clean upstream Kibana `main`. They were measured on the author's machine;
  the builder cannot re-run the gateway or Kibana parts. Treat the guide as the only source for those numbers.
  The stand-in model runs offline, so its outputs (80/90/20/100) can be re-checked locally.
- The deck is the published Slides artifact `claude.ai/artifact/41ux3uSugKicaNt9C4459B`: files under `project/`
  (`deck.json` plus `slides/<id>.html`, inline styles, no `format` key). v2 is created as a new artifact from
  the Slides type; unchanged slides are copied server side with `files` entries of the form `{artifact, path}`.
  The original stays unchanged.

## Resolved reviewer questions (my calls)

- **Rename:** do not rename. Create `lab-a` from `solution` and leave `solution` in place, so the published
  deck and the current guide keep working. The owner can delete `solution` and `lab-b-python` later.
  Pushing new branches is outward-facing, so the builder asks before each push.
- **Times:** hands-on time is the guide's 18 + 7 = 25 min. Session total is computed from the v2 plan
  (intro and anatomy about 8, Lab A 18, Kibana intro about 5, Lab B 7, wrap-up 2, about 40 min) and written once,
  the same on the cover, plan slide and `README.md`.
- **Expected output on slides:** copied from `GUIDE.md` (scores, tables, exit codes), not paraphrased.
  Questions are the guide's own questions where they exist; the builder writes one only for steps without one.
- **Appendix slides:** copied as they are, including the existing `[Fill in...]` placeholders.
- **Kibana version:** `LAB-B.md` states "verified on upstream Kibana `main`, November 2026" and tells
  participants to use a clean `git worktree`, as the guide already does.
- **README:** the branch map lists three branches and says nothing about `lab-b-python`.
- **Merge direction:** fix on `main` first, then merge `main` into `lab-a` and `lab-b` (as done today).

## My calls to check

- `lab-a` ships with all files present (3 branches, no per-step pulling).
- `lab-a` is created from `solution`; `solution` and `lab-b-python` are left alone.
- The Kibana walkthrough moves to a short intro plus an appendix.
- Placeholders in the golden-cluster and security slides stay in the appendix, still marked.
- Session total is about 40 minutes, derived rather than guessed; the exact number is set at build time.

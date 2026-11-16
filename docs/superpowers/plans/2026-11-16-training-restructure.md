# Training Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the evals workshop a repo a participant can follow from the deck alone (branches `main`, `lab-a`, `lab-b`) and a v2 deck that matches it, with `@kbn/evals` as the only Lab B.

**Architecture:** Fix docs on `main` first, then branch `lab-a` from `origin/solution` and `lab-b` from `main`, each adding one lab guide. The deck v2 is a new Slides artifact created from the type; unchanged slides are copied server side from the published deck, new slides are written as files under `project/`.

**Tech Stack:** git, uv, Markdown; Slides artifact (`project/deck.json` plus `project/slides/<id>.html`, inline styles, Space Grotesk / Inter / JetBrains Mono, existing palette).

**Spec:** `docs/superpowers/specs/2026-11-16-training-restructure-design.md`

## Global Constraints

- Branches: `main`, `lab-a` (from `origin/solution`), `lab-b`. `solution` and `lab-b-python` are not touched, renamed or deleted.
- Ask the user before every `git push`. Nothing is force-pushed.
- Lab B is `@kbn/evals` only. No Python SDK, no `kibana_run.py`, no "Lab C" anywhere in v2.
- Published deck `claude.ai/artifact/41ux3uSugKicaNt9C4459B` stays unchanged. v2 is a new artifact.
- Hands-on time is Lab A 18 min plus Lab B 7 min = 25 min. Session total is about 40 min, computed in Task 4 and written identically on cover, plan slide and `README.md`.
- Expected output on slides is copied from `GUIDE.md` (scores, tables, exit codes), not paraphrased.
- Commands are not changed from `GUIDE.md`, except that on `lab-a` the `git checkout origin/solution -- ...` lines are dropped because the files are present.
- Speaker notes: plain text, 4,000 characters at most. No slide text under 24px.
- Appendix slides keep their existing `[Fill in...]` placeholders.
- Bug fixes go on `main` first, then `main` is merged into `lab-a` and `lab-b`.

## Review Focus

- Participant clones, runs `git checkout lab-a`, and the branch does not exist because it was never pushed. Plan pushes both branches (after asking) and verifies with `git ls-remote --heads origin`.
- `lab-a` needs `pydantic-evals` without an extra `uv add`. Verify `pyproject.toml` on `lab-a` lists it and `uv sync` alone makes `uv run python -m evals.check_evaluators` work. If so, the prep slide says `git checkout lab-a` then `uv sync`, not `uv add --dev pydantic-evals` (my call; the spec listed `uv add` before this was checked).
- A leftover `origin/solution`, `lab-b-python`, `kibana_run.py` or `kibana` dependency group reference in v2 slides or either lab guide sends participants to a dead path. Verified by grep in Task 8.
- A time on one slide disagrees with another (cover, plan, divider pills, README). Verified by grep in Task 8.
- The original deck changed by accident. Verified by re-reading its version id in Task 8.

---

### Task 1: `main` documentation (branch map and index)

**Files:**
- Modify: `README.md` (replace the Status paragraph's last two lines with a branch map)
- Modify: `GUIDE.md` (shrink to an index: timing table, setup checklist, links to `LAB-A.md` on `lab-a` and `LAB-B.md` on `lab-b`, stretch goals, troubleshooting kept)

**Interfaces:**
- Produces: the branch names `lab-a` and `lab-b` and the guide file names `LAB-A.md`, `LAB-B.md`, which Tasks 2 to 7 use verbatim.

- [ ] **Step 1: Write the branch map in `README.md`.** A table with three rows: `main` (tool, tests; start here), `lab-a` (Lab A: `LAB-A.md` plus the full `evals/` folder), `lab-b` (Lab B: `LAB-B.md` plus `kbn-evals/`, used inside a Kibana checkout). One line: "Running the session? Start with GUIDE.md." Do not mention `solution` or `lab-b-python`.
- [ ] **Step 2: Shrink `GUIDE.md` to an index.** Keep: the opening paragraph, the Part/Time/Needs table, the setup checklist (with the `uv add --dev pydantic-evals` line replaced by "`git checkout lab-a`, then `uv sync`" only after Task 2 step 3 confirms the dependency is on `lab-a`), the settings table, stretch goals, troubleshooting. Replace the Lab A and Lab B bodies with one line each linking to the guide on its branch. Remove the facilitator note about branches.
- [ ] **Step 3: Verify.** Run: `grep -nE "solution|lab-b-python" README.md GUIDE.md`. Expected: no matches. Run: `grep -nE "lab-a|lab-b" README.md GUIDE.md`. Expected: matches in both files.
- [ ] **Step 4: Commit** `docs: branch map and guide index for lab-a and lab-b`.

### Task 2: `lab-a` branch and `LAB-A.md`

**Files:**
- Create: branch `lab-a` from `origin/solution`, then merge `main` into it
- Create: `LAB-A.md` (Lab A section of the old `GUIDE.md`, rewritten for "files are present")

**Interfaces:**
- Consumes: Task 1 (`main` docs, merged in).
- Produces: step headings `A1` to `A6`, each with command, files, expected output, question. Task 5 builds one slide per heading from this file.

- [ ] **Step 1: Branch.** `git switch -c lab-a origin/solution && git merge main`. Resolve `GUIDE.md` and `README.md` conflicts by taking `main`'s versions.
- [ ] **Step 2: Write `LAB-A.md`.** Same six steps, times and commands as the current Lab A, with: "Everything is already in `evals/`" at the top; A2 and A3 and A4 open the file instead of pulling it; the `git checkout origin/solution -- ...` lines removed; the A6 line `git checkout origin/solution -- .github/workflows/evals.yml` replaced by "Open `.github/workflows/evals.yml`". Keep the expected-output tables and score lines exactly. Add a closing section "Broke something?" with `git checkout origin/lab-a -- evals/`.
- [ ] **Step 3: Verify the stand-in path offline.**
  Run: `uv sync && uv run python -m evals.check_evaluators`. Expected: the four-row table from A3 (✔/✗ pattern as in the guide).
  Run: `uv run python -m evals.run_evals --model stand-in`. Expected: `RiskMatches` 80%, `NoUnderestimate` 90%, `SpecificFocus` 20%, `NotFallback` 100%.
  Run: `grep -c "origin/solution" LAB-A.md`. Expected: `0`.
  Run: `grep -n "pydantic-evals" pyproject.toml`. Expected: one match (decides Task 1 step 2's setup line).
- [ ] **Step 4: Commit** `docs: LAB-A.md for the lab-a branch`.

### Task 3: `lab-b` branch and `LAB-B.md`

**Files:**
- Create: branch `lab-b` from `main` (after Task 1)
- Create: `LAB-B.md` (Lab B section of the old `GUIDE.md` plus the `kbn-evals/README.md` steps)

**Interfaces:**
- Consumes: Task 1.
- Produces: step headings `B1` to `B4` and a gotchas list. Task 6 builds slides from these.

- [ ] **Step 1: Branch.** `git switch -c lab-b main`.
- [ ] **Step 2: Write `LAB-B.md`.** Copy B1 to B4 and the gotchas from the current guide unchanged (smoke test, spec anatomy, run two models, UI compare, `--config`/`--model`/`--judge`, `Project(s) not found`, no-TTY flags, `config.local.json` and EDOT port `:9220` fix). Add at the top: "Verified on upstream Kibana `main`, November 2026. Use a clean `git worktree` (`git worktree add ../kibana-clean origin/main --detach`), then `pnpm kbn bootstrap`." State that `els` is not used.
- [ ] **Step 3: Verify.** Run: `grep -nE "els auth|kibana_run|uv sync --group kibana|Python SDK" LAB-B.md`. Expected: no matches. Run: `ls kbn-evals/evals/pr_triage.spec.ts kbn-evals/playwright.config.ts`. Expected: both exist.
- [ ] **Step 4: Commit** `docs: LAB-B.md for the lab-b branch`.

### Task 4: Deck v2 shell and plan numbers

**Files:**
- Create (scratchpad folder `<root>`): `project/deck.json`, copies of unchanged slides
- Published: new Slides artifact titled "Evals workshop: pr-risk-triager v2"

**Interfaces:**
- Produces: the new artifact `url`, used by Tasks 5 to 8; slide ids below.

Slide ids and order for v2 (existing ids reused where the slide is copied unchanged or lightly edited):
`cover, why, tool, anatomy, repomap, plan, partlaba, a1, a2, a3, checks, a4, evaluators, a5, a6, resultsa, donelaba, partkibana, kbwhere, kbrun, partlabb, b1, b2, b3, b4, bgotchas, resultsb, donelabb, takeaways, prep, appendix, kbgolden, kbui, kbhow, kbsecurity`. Remove: `laba` (replaced by `a1`-`a6`), `labb` (replaced by `b1`-`b4`).

- [ ] **Step 1: Compute the total.** Sum the planned minutes: intro and anatomy and repo map 8, Lab A 18, Kibana intro 5, Lab B 7, wrap-up 2. Write the result once as `TOTAL`; every later task reuses that exact number.
- [ ] **Step 2: Create the artifact** from the Slides type with the title above; one `Artifact` publish with `type_url`, no files (per the type's instructions).
- [ ] **Step 3: Publish the shell.** `project/deck.json` (v4 style, no `format` key, same `faces` as the original, new `order`, `sections` renamed: intro, Lab A, Kibana intro, Lab B, takeaways, appendix) plus the unchanged slides copied with `files` entries `{artifact: "https://claude.ai/artifact/41ux3uSugKicaNt9C4459B", path: "project/slides/<id>.html"}` for: `why, tool, anatomy, checks, evaluators, resultsa, donelaba, kbwhere, kbrun, kbgolden, kbui, kbhow, kbsecurity, donelabb, takeaways`. Slides with edits (`cover, plan, partlaba, partkibana, partlabb, resultsb, prep, donelaba, donelabb`) are written in later tasks; copy them now as placeholders so the deck opens.
- [ ] **Step 4: Verify.** Read the new artifact's `project/deck.json`. Expected: `order` equals the list above and every id has a file.

### Task 5: Repo map, plan, cover and Lab A step slides

**Files:**
- Create: `project/slides/repomap.html`, `a1.html` to `a6.html`
- Modify: `cover.html`, `plan.html`, `partlaba.html`, `donelaba.html`

**Interfaces:**
- Consumes: `LAB-A.md` headings from Task 2; `TOTAL` from Task 4.
- Produces: slide layout "step slide": eyebrow `Lab A · A<n> · <m> min`, `h2` title, command block (JetBrains Mono, 28px, dark panel), a "Files" line, an "Expect" block, a "Question" line; footer `Evals workshop · pr-risk-triager`. Task 6 reuses this layout for B steps.

- [ ] **Step 1: `repomap.html`.** Three cards for `main`, `lab-a`, `lab-b` (what each holds, which lab uses it), the clone command, and the line `git checkout lab-a`. Notes: how to switch branches and what to do if checkout says the branch does not exist (`git fetch origin`).
- [ ] **Step 2: `a1.html` to `a6.html`.** One slide each from `LAB-A.md`: commands verbatim, files named, expected output copied from the guide (A3 table, A4 stand-in scores and the signed-out `ELS_BIN=false` result, A6 gate results and the model comparison), the guide's question for the step (A1: "would you let this rate PRs for your team?"; A2: add a case and agree its label with your neighbour; A4: which cases would make it fail?). Speaker notes carry TIME, what to watch for, and the 401/403/429 meanings.
- [ ] **Step 3: Update `cover`, `plan`, `partlaba`, `donelaba`.** Cover and plan use `TOTAL` and 25 min hands-on; plan table has three parts (Lab A 18, Kibana intro 5, Lab B 7) and no Lab C; progress pills use the new minutes; `partlaba` says the files are already on the `lab-a` branch.
- [ ] **Step 4: Publish** the new and changed files to the v2 `url` in one call, deck index included (order unchanged from Task 4).
- [ ] **Step 5: Verify.** Read back `a3.html` and `a4.html`. Expected: the four-row evaluator table and `80% / 90% / 20% / 100%` are present. Preview slide `a4` once with the viewer reference to check text fits inside the canvas.

### Task 6: Lab B step slides and results

**Files:**
- Create: `project/slides/b1.html` to `b4.html`, `bgotchas.html`
- Modify: `partlabb.html`, `resultsb.html`, `donelabb.html`

**Interfaces:**
- Consumes: `LAB-B.md` headings from Task 3; step-slide layout from Task 5.

- [ ] **Step 1: `b1.html` to `b4.html`.** One slide per step from `LAB-B.md`: B1 smoke test, B2 add and read the spec (the dataset/task/evaluators anatomy from the guide), B3 run two models with the `--config --model --judge` command, B4 compare in the UI (`/app/management/ai/evals` → Experiments → Compare selected; `EVAL_KBN_URL` for `compare`). Each shows command, files, expected result, one question.
- [ ] **Step 2: `bgotchas.html`.** Table from the guide's Lab B gotchas: `Project(s) not found`, no TTY, `fetch failed` on `:5601`, null token scores and the `:9220` EDOT fix, `Inference with id ... already exists`.
- [ ] **Step 3: `resultsb.html`.** Replace the Python-SDK example with the verified `@kbn/evals` run from the guide: `eis-google-gemini-3-0-flash` vs `eis-openai-gpt-5-2`, judge `eis-anthropic-claude-4-6-sonnet`, 2 passed in about 3.6 min. State that the guide holds no per-evaluator scores for this run; the slide shows only those facts plus the caveat "yours will differ".
- [ ] **Step 4: Update `partlabb`, `donelabb`** (minutes, goal text, `@kbn/evals`, "Kibana checkout needed").
- [ ] **Step 5: Publish** new and changed files to the v2 `url`.
- [ ] **Step 6: Verify.** Run (on local copies): `grep -rnE "kibana_run|lab-b-python|--group kibana|gateway: no Kibana connector" <root>/project/slides`. Expected: no matches.

### Task 7: Kibana intro, appendix, prep

**Files:**
- Create: `project/slides/appendix.html`
- Modify: `partkibana.html`, `kbwhere.html`, `kbrun.html` (trim to intro length), `prep.html`, `deck.json`

- [ ] **Step 1: Kibana intro.** `partkibana` says 5 minutes; keep `kbwhere` and `kbrun` as the two intro slides (notes trimmed to about 2 and 3 minutes). `kbgolden`, `kbui`, `kbhow`, `kbsecurity` stay as copied, now after `takeaways` behind an `appendix` divider slide ("Appendix: not needed for the labs").
- [ ] **Step 2: `prep.html`.** Setup rows: clone URL; `git checkout lab-a` then `uv sync`; `els auth login --env prod`; for Lab B, `corepack enable`, `corepack prepare pnpm@12.4.2 --activate`, `pnpm kbn bootstrap`, `node scripts/evals doctor` in a clean worktree. Remove the `lab-b-python` and `--group kibana` lines. Keep the stand-in note.
- [ ] **Step 3: Publish** with `deck.json` last.
- [ ] **Step 4: Verify.** Read `project/deck.json`; `order` ends `takeaways, prep, appendix, kbgolden, kbui, kbhow, kbsecurity`.

### Task 8: Cross-check and handoff

- [ ] **Step 1: Consistency greps on local copies.** `grep -rnE "[0-9]+ min" <root>/project/slides/cover.html <root>/project/slides/plan.html README.md`. Expected: the session total equals the `TOTAL` from Task 4 on all three, and Lab A/Kibana intro/Lab B minutes equal 18/5/7 everywhere they appear. `grep -rnE "origin/solution|lab-b-python|Lab C" <root>/project/slides README.md GUIDE.md LAB-A.md LAB-B.md` run per branch. Expected: none.
- [ ] **Step 2: Original untouched.** Read the original artifact's version id. Expected: `1794828647-d170` or later only if the user edited it, and no publish from this plan.
- [ ] **Step 3: Slide limits.** Check each new slide's notes length (4,000 max) and that no font-size below 24px appears.
- [ ] **Step 4: Push (ask first).** Show the user the branch list and commits; after approval run `git push origin main lab-a lab-b`. Then `git ls-remote --heads origin`. Expected: `main`, `lab-a`, `lab-b`, `solution`, `lab-b-python`.
- [ ] **Step 5: Hand over** the v2 link, the three branches, and the list of choices (the prep `uv sync` setup line, `resultsb` limited to guide facts).

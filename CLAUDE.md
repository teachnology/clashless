# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Clashless is a scheduling optimisation solver: given a set of presentations (each with a unique id
and a list of participants — unique within that presentation, unbounded, with no distinguished
chair role) plus a session label per presentation identifying which parallel room/track it belongs
to, and a table of per-person unavailability rules, it assigns presentations to (day, slot) pairs
such that no person is double-booked, no two presentations sharing a session collide, and no one is
scheduled during a time they marked unavailable.

The conference runs over `n_days` days; each day has the same `n_slots` slots — a plain count, not
a table of clock times, since clashless has no notion of clock time at all — and multiple sessions
run in parallel each day across multiple rooms/tracks. A "session" is a plain, caller-supplied
label (any hashable value) identifying which room/track a presentation belongs to. Unlike an
earlier design where "room" was derived from who chaired a presentation, a session is just an
explicit scheduling resource alongside day/slot, decoupled from any person's identity — many
presentations can share a session label across different days without conflict, only a same-day,
same-slot clash matters.

The public API is `Participants`, `Sessions`, and `Unavailability` (one class per input, each
exposing the parsed structure as `.data`), passed into `Schedule(participants, sessions,
unavailability, n_days, n_slots)`. None of the three reads files or accepts `pandas` objects — each
takes a plain Python `dict` as its first argument: `Participants` takes `{id: [participant, ...]}`,
`Sessions` takes `{id: session_label}`, `Unavailability` takes `{person: [(day, slot), ...]}` with
`None` as the wildcard marker. Loading from a CSV is entirely the caller's job (`pandas` is a
convenient way to do it, as tests/tutorials show, but clashless itself never requires it at the
input boundary) — there is no shared loading helper in `src/clashless/`, and none of the three
classes takes a `columns` remapping parameter any more, since a caller building a dict already
controls exactly which keys go into it.

`Participants` enforces the one invariant that matters for its own correctness: every presentation
has at least one participant (`ValueError` on an empty list) and no participant repeats within one
presentation's own list (`ValueError` on an in-row duplicate) — dict keys already guarantee id
uniqueness structurally, so there's no separate uniqueness check to make. `Sessions` is a thin
wrapper with no validation of its own. `Schedule.__init__` is where `participants`/`sessions`
consistency is checked instead, since only there are both objects available together: it raises
`ValueError` immediately if their id sets don't match exactly. `Unavailability` does no shape
validation either — it's a thin wrapper whose `.data` *is* the same `{person: [(day, slot), ...]}`
cache `is_unavailable(person, day, slot)` looks up directly (no `groupby` needed at construction
time any more, since the input is already in that shape).

Any check a user might want to run by hand on a *solved* schedule lives in `clashless.isvalid`
(`src/clashless/isvalid.py`) — it never raises, only prints a report and returns a bool:
`isvalid.schedule(schedule, participants, sessions, unavailability)` re-checks a solved schedule
for double-booking, session clashes, and unavailability violations, returning `True` if none are
found — a reassurance check for a schedule built or edited outside `Schedule.solve()` (which
already guarantees this internally). There used to be an `isvalid.report(presentations)` function
summarizing role-column repetition; it's gone entirely, since `Participants` now enforces the
relevant invariant (no in-row duplicates) at construction rather than needing a separate report to
surface it.

Tests, tutorials, and other external code prefer `import clashless as cl` + `cl.Name` over
`from clashless import Name` (matches the pattern used for `pd`/`np`); this doesn't apply inside
`src/clashless/` itself, where submodules import directly from each other.

`Schedule.solve()` returns a `dict` `{id: {"day": ..., "slot": ...}}`, or raises
`clashless.SchedulingError` if no valid schedule exists for the given `n_days`/`n_slots`. It's
implemented as a CP-SAT model (`ortools`) in `src/clashless/schedule.py`: one slot variable per
presentation (domain pruned by unavailability) plus two `AllDifferent` constraint groups — one per
person across every presentation they appear in (`participants.data`), and one per session across
every presentation that shares it (`sessions.data`). The person constraint enforces "no
double-booking"; the session constraint enforces "no two presentations in the same room at once" —
what a chair-derived room used to guarantee implicitly, now an explicit constraint since there's no
chair identity to piggyback on. Presentations with disjoint people *and* different sessions are
never constrained against each other, so parallel rooms are naturally unlimited. `solve()` either
succeeds completely or raises.

On top of that hard-constraint model, `solve()` also optimizes for schedule *quality*: a weighted
objective, summed over every person appearing in any presentation's participants list, that
primarily minimizes each person's number of distinct active days (maximizing whole days off), and
secondarily
(much lower weight, by default — always dominating any possible change in the secondary term)
minimizes each active day's slot "spread" (last − first slot used), rewarding back-to-back slots
over scattered ones. This turns `solve()` into a genuine optimization rather than "stop at the
first feasible solution," so it's best-effort within a time budget — CP-SAT's `FEASIBLE` status
(valid but not proven optimal) is accepted, same as `OPTIMAL`; only grouping *quality* is
time-boxed, hard constraints are never relaxed.

`solve()` warm-starts the objective search (`_solve_for_warm_start` in `schedule.py`): it first
solves the hard-constraint model with no objective (fast — nothing to search for beyond one
feasible solution), then hints every variable in the grouping objective — not just the slot
variables — with values computed directly from that solution, so CP-SAT starts from a fully
consistent, already-feasible incumbent rather than needing to rediscover feasibility inside the
much larger objective-laden model. This exists because of a real regression found while writing
the tutorial series (see `test_grouping_is_never_worse_than_not_grouping`): without it, grouping
could reproducibly do *worse* than not grouping at all — CP-SAT could spend most of the time budget
just reaching feasibility inside the bigger model, worse than the accidental compactness a plain
feasibility-only solve tends to find (slot indices are numbered day-major, so filling them in order
happens to pack days fairly tightly already).

The warm-start closes the worst pathological cases but is not a complete fix — verified
empirically (multiple repeated runs, not a one-off) that at real scale (the ~290-presentation
`large_synthetic` fixture, `n_days=10`), `optimize_grouping=True` at the default 30s budget is
*not* reliably better than `optimize_grouping=False` on average, let alone consistently so — the
grouping objective's auxiliary variables (thousands of them at that scale) mean CP-SAT spends most
of its budget on bookkeeping rather than genuine improvement. This is a known, documented
limitation, not something to "fix" by tweaking test fixtures — a real efficiency improvement to the
objective's model would be a separate, substantial piece of work. Practical implication: at large
scale, don't trust the default budget to help — increase `max_solve_seconds` substantially and
compare against `optimize_grouping=False` on your own data before relying on the result. This is
also why `large_synthetic`'s `Schedule` test stays a validity-only smoke test (see below), and why
the tutorial series demonstrates grouping quality on `several_competing_moderators` instead, where
it's reliable.

`Schedule.__init__` exposes four parameters controlling this, all optional with defaults matching
the behaviour above: `optimize_grouping=True` (set `False` to skip building the objective
entirely — not just ignore it — reverting to the old fast feasibility-only solve, a genuine speed
win rather than a smaller model), `active_day_weight=None` (default `n_days * n_slots`),
`spread_weight=1`, and `max_solve_seconds=30.0` (CP-SAT's best-effort time budget).

`plot_schedule(schedule, participants, sessions, n_days, n_slots, slot_labels=None)`
(`src/clashless/plotting.py`) renders a solved schedule as an interactive Plotly timetable:
sessions on the x-axis, chronological `Day · slot` rows on the y-axis — both positional, so
room/time identity never needs a color — and a single accent color marking occupied cells, each
labelled with its presentation id (hover shows the full detail: id, participants, and session).
`n_days`/`n_slots` are explicit parameters (not derived from the schedule dict), so the rendered
grid always matches the solver's declared capacity even if some slots end up unused. `slot_labels`,
if given, is an optional `{slot_number: "09:00"}` map for cosmetic row labels only — entirely
decoupled from `Schedule`/solving (there's no more `SessionTimes`/clock-time concept anywhere in
the core library); missing/omitted entries fall back to a plain `"Slot N"` label.
`export_schedule_to_excel(schedule, participants, sessions, n_days, n_slots, path,
slot_labels=None)` writes the same room x time grid to an `.xlsx` file (via `openpyxl`) — since a
spreadsheet has no hover, every occupied cell's full detail is written directly as wrapped text
instead of just an id. Both functions share a private `_build_grid` helper so the two stay in
lockstep on layout.

## Commands

This project uses `uv` for dependency and environment management (Python >=3.14, `uv_build`
backend).

- Install/sync dependencies: `uv sync`
- Run the full test suite: `uv run pytest` — `[tool.pytest.ini_options]` bakes `-n auto
  --dist=loadscope` (pytest-xdist, parallel), `--doctest-modules` (collects any doctests in
  `src/`; there are none yet, so currently a no-op), and `--cov=clashless --cov-report=html
  --cov-report=term` (pytest-cov) into `addopts`, so these run by default rather than needing
  extra flags. `--dist=loadscope` is required, not optional: nbval runs a notebook's cells as
  separate pytest items that share kernel state cell-to-cell, and plain `-n auto` load-balances
  items individually across workers - splitting a notebook's cells across separate worker
  processes (each with its own kernel) and breaking on the first `NameError` from a variable
  defined in an earlier cell. `loadscope` keeps every item from the same parent (each notebook
  file, each test module) on one worker, so cell order/state stays intact.
- Run a single test file: `uv run pytest tests/test_foo.py`
- Run a single test: `uv run pytest tests/test_foo.py::test_name`
- Run the tutorial notebook(s) under `docs/` as tests (nbval, lax mode — only fails on a cell
  raising, not on output differences, since the CP-SAT solver isn't guaranteed to return the same
  schedule byte-for-byte across runs): `uv run pytest --nbval-lax docs`
- Lint: `uvx ruff check .` — format check: `uvx ruff format --check .` (`uvx` runs ruff from its
  own isolated environment, not the project's, so this works without `uv sync` first; CI uses this
  too — see below). `[tool.ruff] extend-include = ["*.ipynb"]`, so both commands also cover every
  notebook under `docs/tutorials/` and `tests/datamaker.ipynb`, not just `.py` files.
- Add a runtime dependency: `uv add <package>`
- Add a dev-only dependency: `uv add --group dev <package>`

CI (`.github/workflows/`) runs on push to `main` and on every pull request: `tests.yml` runs
`uv sync --all-groups` then the two commands above (test suite + nbval); `ruff.yml` runs the two
`uvx ruff` commands directly, with no project sync at all. `release.yml` triggers on a published
GitHub release, re-runs both the test suite and ruff, then builds with `uv build` and publishes to
PyPI via `uv publish --trusted-publishing always`.

`changes.md` at the repo root is the running roadmap/TODO checklist for this project (docstrings,
Sphinx docs, README content, etc.) - check it for planned-but-not-yet-done work before assuming
something is out of scope.

## Architecture and data model

The package uses the standard `src/` layout (`src/clashless/`).

The domain model, as reflected in `tests/data` (generated by `tests/datamaker.ipynb` using
`fakeitmakeit` and `pandas`), revolves around three structures:

- **`participants.csv`** — long format, one row per `(id, participant)` pair: every presentation's
  participant list unrolled flat, since the list is variable-length and can't fit fixed columns.
  Loaders group by `id` to rebuild each presentation's list (see `tests/conftest.py`'s
  `read_participants`). The only invariants `Participants` itself enforces are non-empty and no
  in-row duplicates — see above. `tests/data`'s fixtures still generate data that *looks* like a
  real conference (one clearly-unique "anchor" person per presentation, a moderator drawn from a
  small pool of the others) since that's what makes a realistic test fixture, but that's a
  generator choice, not something `Participants` checks. A moderator who is also one of the other
  participants (self-chairing, in the old terminology) is deliberately generated in
  `large_synthetic` and deduplicated when unrolled into `participants.csv`, since `Participants`
  now rejects an in-row duplicate that the old `Presentations` allowed.
- **`sessions.csv`** — one row per presentation: `id`, `session`. `tests/data`'s fixtures reuse each
  presentation's moderator name as its session label (preserving each scenario's original
  room-partitioning intent from before this label became explicit), but the label itself is just an
  opaque value to clashless - any hashable session id works.
- **`unavailable.csv`** — one row per unavailability rule: `person`, nullable `day`, nullable
  `slot`. The nullability of `day`/`slot` encodes the rule scope (a `NaN`/`<NA>` at the CSV level,
  converted to Python `None` when loaded into `Unavailability`, acts as a wildcard over that
  column):
  - `day` set, `slot` null → unavailable **all day** on that day
  - `day` null, `slot` set → unavailable during that slot **every day**
  - both set → unavailable for that specific `(day, slot)` only
  - both null → unavailable for the **entire conference**

  A single person may have multiple restriction rows (e.g. a specific slot plus a whole day).

`grouped_into_fewest_days` and `few_presentations_back_to_back` test the grouping objective above.
Both need genuine cross-contention to be meaningful: two people who each need every one of their
own presentations at a distinct slot, sharing just enough participants with each other's
presentations that a non-optimizing solver can end up interleaving them across more days/slots
than necessary. A version of these fixtures with only one repeated person (no competing session)
passed even *before* the objective was implemented, purely because CP-SAT's default search happens
to pack low slot indices first — worth remembering if you add more grouping-objective fixtures.
`several_competing_moderators` (32 presentations, 4 people who each moderate 8 presentations and
give their name to that group's session, pairwise sharing a participant) is the right-sized
fixture for testing `optimize_grouping`/`max_solve_seconds`, and for
`test_grouping_is_never_worse_than_not_grouping` (the regression test for the warm-start fix
above): small enough to reach feasibility instantly, but with the objective on and its default 30s
budget, genuinely hard enough to *optimize* that it uses the whole budget — giving a real, reliable
contrast for the on/off toggle, a reduced time budget, and grouping-quality comparisons, unlike
`large_synthetic` (too slow to reach feasibility quickly once the objective's auxiliary variables
are attached, and not reliably improved by grouping at all within reasonable time — see above) or
the tiny fixtures above (solve instantly either way, so nothing meaningful to bound or compare).
This same fixture is reused (via relative path from `docs/tutorials/`) as the main worked example
in the tutorial series - see below.

Tests are fixture-driven from `tests/data/<scenario_name>/` — one directory per scenario, each
containing only the files that scenario needs (pure `Participants` loading tests need only
`participants.csv`). `tests/conftest.py` provides `load_scenario(name)` and a shared
`assert_valid_schedule(...)` validator encoding the hard constraints above, reused across
`test_schedule.py` instead of re-deriving checks per test. `tests/data/large_synthetic/` is the one
generated-at-scale fixture (via `tests/datamaker.ipynb`, ~290 presentations, 6 sessions, 8
slots/day) — note its `unavailable.csv` deliberately never generates a "global" (entire-
conference) restriction, since at that scale a single globally-blocked moderator (who's in dozens
of presentations) would make the whole fixture unsatisfiable; and its `Schedule` test uses more
`n_days` than the day range referenced in its unavailability rules, to give the busiest person
(up to ~53 presentations) enough slot capacity — see the comment in `test_schedule.py` for the
exact numbers if you regenerate this fixture.

## Tutorials

`docs/tutorials/` is a three-part "getting started" series, each notebook independently runnable
(no notebook depends on another having been run first) and covered by `nbval` in CI:

1. `01_preparing_your_data.ipynb` — builds a small example conference by hand, explaining
   `Participants`/`Sessions`/`Unavailability` as plain dicts, the new `ValueError` on a duplicate
   participant within one presentation, and saves it to `docs/tutorials/data/small_conference/`
   (its own docs-local fixture, independent of `tests/`).
2. `02_creating_a_schedule.ipynb` — loads that same data, solves with `optimize_grouping=False`
   (deliberately, to isolate the basics before tutorial 3), covers `SchedulingError`, the result's
   dict shape, looking it up against `participants.data`/`sessions.data`, `plot_schedule`, and
   `export_schedule_to_excel`.
3. `03_making_schedules_compact.ipynb` — the grouping objective, using `tests/data/
   several_competing_moderators` (not `large_synthetic` — see above for why), plus an honest note
   on where the default time budget currently stops being enough at real scale.

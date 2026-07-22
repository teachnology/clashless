# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Clashless is a scheduling optimisation solver: given a set of presentations (each with four fully
symmetric roles - three participants and a chair), a set of per-day session start times, and a
table of per-person unavailability rules, it assigns presentations to (day, session, room) slots
such that no person is double-booked and no one is scheduled during a time they marked
unavailable.

The conference runs over `n_days` days; each day has the same `n_sessions` sessions (see
`session-start-times.csv` for example start times), and multiple sessions run in parallel each
day across multiple rooms/tracks. There is no independent room id — the room for a given day is
determined by the chair: each chair runs one room for the whole day, so all presentations they
chair that day share that room, and different chairs active on the same day occupy different
parallel rooms. A room is therefore just "the set of presentations chaired by person C on day D"
rather than a separate schedulable resource.

The public API is `Presentations`, `Unavailability`, and `SessionTimes` (one class per input table,
each exposing the parsed table as `.data`), passed into `Schedule(presentations, unavailability,
session_times, n_days)`. Each of the three accepts a CSV path or an in-memory `pd.DataFrame`
(`SessionTimes` also accepts a `pd.Series`, its natural single-column shape) as its first
argument, plus an optional `columns` mapping from your own column names to the ones clashless
expects — e.g. `Presentations(df, columns={"student": "participant_1"})` — so callers don't have
to rename their own data by hand first. This is implemented by a shared private helper,
`clashless._io.load_table`, used by all three classes.

`Presentations` itself enforces nothing about repetition (see below) — `clashless.isvalid.report
(presentations)` (`src/clashless/isvalid.py`) is the informational replacement: it prints a short
summary of per-column uniqueness, how often the same person holds two roles within one
presentation's own row, and who appears most often overall. It never raises; it's a diagnostic to
run by hand, not a gate `solve()` depends on. `Schedule.solve()` returns a `DataFrame` indexed by presentation `id` with
`day`/`session` columns, or raises `clashless.SchedulingError` if no valid schedule exists for the
given `n_days`. It's implemented as a CP-SAT model (`ortools`) in `src/clashless/schedule.py`: one
slot variable per presentation (domain pruned by unavailability) plus an `AllDifferent` constraint
per person across every presentation they appear in (as participant_1/2/3/chair) — this single
constraint enforces both "no double-booking" and "a chair can't chair two rooms at once", and
naturally allows unlimited parallel rooms since presentations with disjoint people are never
constrained against each other. `solve()` either succeeds completely or raises.

On top of that hard-constraint model, `solve()` also optimizes for schedule *quality*: a weighted
objective, summed over every person appearing in any of the four role columns (no role is excluded
- since the roles are fully symmetric, no column is guaranteed to appear at most once per person),
that primarily minimizes each person's number of distinct active days (maximizing whole days off),
and secondarily
(much lower weight, by default — always dominating any possible change in the secondary term)
minimizes each active day's session "spread" (last − first session used), rewarding back-to-back
sessions over scattered ones. This turns `solve()` into a genuine optimization rather than "stop at
the first feasible solution," so it's best-effort within a time budget — CP-SAT's `FEASIBLE` status
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
win rather than a smaller model), `active_day_weight=None` (default `n_days * n_sessions`),
`spread_weight=1`, and `max_solve_seconds=30.0` (CP-SAT's best-effort time budget).

`plot_schedule(schedule, presentations, session_times)` (`src/clashless/plotting.py`) renders a
solved schedule as an interactive Plotly timetable: chairs on the x-axis, chronological
`Day · session` slots on the y-axis — both positional, so room/time identity never needs a color —
and a single accent color marking occupied cells, each labelled with its presentation id (hover
shows the full detail: id, the three participants, and the chair). It always draws the full day
range present in the `schedule` passed in, so callers zoom by filtering the DataFrame first (e.g.
`schedule[schedule["day"] <= 2]`) rather than via a parameter.
`export_schedule_to_excel(schedule, presentations, session_times, path)` writes the same room x
time grid to an `.xlsx` file (via `openpyxl`) — since a spreadsheet has no hover, every occupied
cell's full detail is written directly as wrapped text instead of just an id. Both functions share
a private `_build_grid` helper so the two stay in lockstep on layout.

## Commands

This project uses `uv` for dependency and environment management (Python >=3.14, `uv_build`
backend).

- Install/sync dependencies: `uv sync`
- Run the full test suite: `uv run pytest`
- Run a single test file: `uv run pytest tests/test_foo.py`
- Run a single test: `uv run pytest tests/test_foo.py::test_name`
- Run tests in parallel (pytest-xdist is a dev dependency): `uv run pytest -n auto`
- Run tests with coverage (pytest-cov is a dev dependency): `uv run pytest --cov=clashless`
- Run the tutorial notebook(s) under `docs/` as tests (nbval, lax mode — only fails on a cell
  raising, not on output differences, since the CP-SAT solver isn't guaranteed to return the same
  schedule byte-for-byte across runs): `uv run pytest --nbval-lax docs`
- Lint: `uvx ruff check .` — format check: `uvx ruff format --check .` (`uvx` runs ruff from its
  own isolated environment, not the project's, so this works without `uv sync` first; CI uses this
  too — see below)
- Add a runtime dependency: `uv add <package>`
- Add a dev-only dependency: `uv add --group dev <package>`

CI (`.github/workflows/`) runs on push to `main` and on every pull request: `tests.yml` runs
`uv sync --all-groups` then the two commands above (test suite + nbval); `ruff.yml` runs the two
`uvx ruff` commands directly, with no project sync at all.

## Architecture and data model

The package uses the standard `src/` layout (`src/clashless/`) and ships a `py.typed` marker, so
public APIs are expected to be fully type-annotated.

The domain model, as reflected in `tests/data` (generated by `tests/datamaker.ipynb` using
`fakeitmakeit` and `pandas`), revolves around three tables:

- **`presentations.csv`** — one row per presentation: `id` (index), `participant_1`,
  `participant_2`, `participant_3`, `chair`. All four role columns are fully symmetric and
  nothing about repetition is enforced: the same person may appear in more than one role, any
  number of times, including more than once within the same presentation's own row (e.g. a
  participant chairing their own session). There are no invariants to violate — no uniqueness, no
  distinctness between columns, nothing. `tests/data`'s fixtures still generate data that *looks*
  like a real conference (one clearly-unique "anchor" person per row, chairs drawn from a small
  pool of the others) since that's what makes a realistic test fixture, but that's a generator
  choice, not something `Presentations` checks.
- **`session-start-times.csv`** — one row per `session` (int) giving its `start_time`; the same
  `n_sessions` start times apply on every one of the `n_days` conference days. `(day, session)`
  identifies a time slot, but not a room — see the room model above.
- **`unavailable.csv`** — one row per unavailability rule: `person`, nullable `day`, nullable
  `session`. The nullability of `day`/`session` encodes the rule scope (a `NaN`/`<NA>` acts as a
  wildcard over that column):
  - `day` set, `session` null → unavailable **all day** on that day
  - `day` null, `session` set → unavailable during that session **every day**
  - both set → unavailable for that specific `(day, session)` slot only
  - both null → unavailable for the **entire conference**

  A single person may have multiple restriction rows (e.g. a specific slot plus a whole day).

`grouped_into_fewest_days` and `few_presentations_back_to_back` test the grouping objective above.
Both need genuine cross-contention to be meaningful: two chairs who each need every one of
their own presentations at a distinct slot, sharing just enough participants with each other's
presentations that a non-optimizing solver can end up interleaving them across more days/sessions
than necessary. A version of these fixtures with only one repeated person (no competing chair)
passed even *before* the objective was implemented, purely because CP-SAT's default search happens
to pack low slot indices first — worth remembering if you add more grouping-objective fixtures.
`several_competing_moderators` (32 presentations, 4 chairs pairwise sharing a participant) is the
right-sized fixture for testing `optimize_grouping`/`max_solve_seconds`, and for
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
containing only the CSVs that scenario needs (pure `Presentations` loading tests need only
`presentations.csv`). `tests/conftest.py` provides `load_scenario(name)` and a shared
`assert_valid_schedule(...)` validator encoding the hard constraints above, reused across
`test_schedule.py` instead of re-deriving checks per test. `tests/data/large_synthetic/` is the one
generated-at-scale fixture (via `tests/datamaker.ipynb`, ~290 presentations, 6 chairs, 8
sessions/day) — note its `unavailable.csv` deliberately never generates a "global" (entire-
conference) restriction, since at that scale a single globally-blocked chair (who chairs dozens
of presentations) would make the whole fixture unsatisfiable; and its `Schedule` test uses more
`n_days` than the day range referenced in its unavailability rules, to give the busiest chair
(up to ~53 presentations) enough slot capacity — see the comment in `test_schedule.py` for the
exact numbers if you regenerate this fixture.

## Tutorials

`docs/tutorials/` is a three-part "getting started" series, each notebook independently runnable
(no notebook depends on another having been run first) and covered by `nbval` in CI:

1. `01_preparing_your_data.ipynb` — builds a small example conference by hand, explaining
   `Presentations`/`SessionTimes`/`Unavailability`, the fully-symmetric role columns, and
   `clashless.isvalid.report`, and saves it to `docs/tutorials/data/small_conference/` (its own
   docs-local fixture, independent of `tests/`).
2. `02_creating_a_schedule.ipynb` — loads that same data, solves with `optimize_grouping=False`
   (deliberately, to isolate the basics before tutorial 3), covers `SchedulingError`, the result's
   shape, joining it back to the input data, `plot_schedule`, and `export_schedule_to_excel`.
3. `03_making_schedules_compact.ipynb` — the grouping objective, using `tests/data/
   several_competing_moderators` (not `large_synthetic` — see above for why), plus an honest note
   on where the default time budget currently stops being enough at real scale.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Clashless is a scheduling optimisation solver: given a set of conference presentations (each
with a student, two supervisors, and a moderator), a set of per-day session start times, and a
table of per-person unavailability rules, it assigns presentations to (day, session, room) slots
such that no person is double-booked and no one is scheduled during a time they marked
unavailable.

The conference runs over `n_days` days; each day has the same `n_sessions` sessions (see
`session-start-times.csv` for example start times), and multiple sessions run in parallel each
day across multiple rooms/tracks. There is no independent room id — the room for a given day is
determined by the moderator acting as session chair: each moderator chairs one room for the whole
day, so all presentations they moderate that day share that room, and different moderators active
on the same day occupy different parallel rooms. A room is therefore just "the set of
presentations chaired by moderator M on day D" rather than a separate schedulable resource.

The public API is `Presentations`, `Unavailability`, and `SessionTimes` (one class per input CSV,
each exposing the parsed table as `.data`), passed into `Schedule(presentations, unavailability,
session_times, n_days)`. `Schedule.solve()` returns a `DataFrame` indexed by presentation `id` with
`day`/`session` columns, or raises `clashless.SchedulingError` if no valid schedule exists for the
given `n_days`. It's implemented as a CP-SAT model (`ortools`) in `src/clashless/schedule.py`: one
slot variable per presentation (domain pruned by unavailability) plus an `AllDifferent` constraint
per person across every presentation they appear in (as student/s1/s2/moderator) — this single
constraint enforces both "no double-booking" and "a moderator can't chair two rooms at once", and
naturally allows unlimited parallel rooms since presentations with disjoint people are never
constrained against each other. `solve()` either succeeds completely or raises.

On top of that hard-constraint model, `solve()` also optimizes for schedule *quality*: a weighted
objective, summed over every person appearing as `s1_name`/`s2_name`/`moderator` (never `student`
— they only ever have their own one presentation, so there's nothing to group), that primarily
minimizes each person's number of distinct active days (maximizing whole days off), and secondarily
(much lower weight — `active_day_weight = n_days * n_sessions`, always dominating any possible
change in the secondary term) minimizes each active day's session "spread" (last − first session
used), rewarding back-to-back sessions over scattered ones. This turns `solve()` into a genuine
optimization rather than "stop at the first feasible solution," so it's best-effort within a time
budget (`MAX_SOLVE_SECONDS = 30.0` in `schedule.py`) — CP-SAT's `FEASIBLE` status (valid but not
proven optimal) is accepted, same as `OPTIMAL`; only grouping *quality* is time-boxed, hard
constraints are never relaxed. At real scale (the ~290-presentation `large_synthetic` fixture),
30s only gets partway to optimal grouping — verified empirically that giving it much longer (~180s)
continues to visibly improve grouping — which is why that fixture's test stays a validity-only
smoke test rather than asserting a specific grouping quality (see below).

`plot_schedule(schedule, presentations, session_times)` (`src/clashless/plotting.py`) renders a
solved schedule as an interactive Plotly timetable: moderators on the x-axis, chronological
`Day · session` slots on the y-axis — both positional, so room/time identity never needs a color —
and a single accent color marking occupied cells, each labelled with its presentation id (hover
shows the full detail: id, student, both supervisors, moderator). It always draws the full day
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
`uv sync --all-groups` then the two commands above (test suite + nbval); `lint.yml` runs the two
`uvx ruff` commands directly, with no project sync at all.

## Architecture and data model

The package uses the standard `src/` layout (`src/clashless/`) and ships a `py.typed` marker, so
public APIs are expected to be fully type-annotated.

The domain model, as reflected in `tests/data` (generated by `tests/datamaker.ipynb` using
`fakeitmakeit` and `pandas`), revolves around three tables:

- **`presentations.csv`** — one row per presentation: `id` (index), `student`, `s1_name`
  (supervisor 1), `s2_name` (supervisor 2), `moderator`. A person can appear as a supervisor
  across many presentations and as moderator for many others; moderators are drawn from a small
  subset of supervisors, so the moderator for a presentation is very often one of that same
  presentation's own `s1_name`/`s2_name` — i.e. a supervisor chairing their own session — and the
  four name slots (`student`, `s1_name`, `s2_name`, `moderator`) do not have to be pairwise
  distinct. Invariants: `student` is unique, `s1_name != s2_name`, and a student is never their own
  supervisor.
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
Both need genuine cross-contention to be meaningful: two moderators who each need every one of
their own presentations at a distinct slot, sharing just enough supervisors with each other's
presentations that a non-optimizing solver can end up interleaving them across more days/sessions
than necessary. A version of these fixtures with only one repeated person (no competing moderator)
passed even *before* the objective was implemented, purely because CP-SAT's default search happens
to pack low slot indices first — worth remembering if you add more grouping-objective fixtures.

Tests are fixture-driven from `tests/data/<scenario_name>/` — one directory per scenario, each
containing only the CSVs that scenario needs (pure `Presentations` validation tests need only
`presentations.csv`). `tests/conftest.py` provides `load_scenario(name)` and a shared
`assert_valid_schedule(...)` validator encoding the hard constraints above, reused across
`test_schedule.py` instead of re-deriving checks per test. `tests/data/large_synthetic/` is the one
generated-at-scale fixture (via `tests/datamaker.ipynb`, ~290 presentations, 6 moderators, 8
sessions/day) — note its `unavailable.csv` deliberately never generates a "global" (entire-
conference) restriction, since at that scale a single globally-blocked moderator (who chairs dozens
of presentations) would make the whole fixture unsatisfiable; and its `Schedule` test uses more
`n_days` than the day range referenced in its unavailability rules, to give the busiest moderator
(up to ~53 presentations) enough slot capacity — see the comment in `test_schedule.py` for the
exact numbers if you regenerate this fixture.

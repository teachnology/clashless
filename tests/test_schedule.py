import time

import pytest
from conftest import assert_valid_schedule, load_scenario

from clashless import Schedule, SchedulingError

# Generous enough to never flake on a slow CI runner, but far enough below the
# 30s default that it clearly proves the toggle/time-budget actually took effect.
FAST_SOLVE_CEILING_SECONDS = 10


def _solve(scenario_name: str, n_days: int):
    scenario = load_scenario(scenario_name)
    schedule = Schedule(
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days,
    ).solve()
    return scenario, schedule


def test_feasible_minimal_produces_a_valid_schedule():
    scenario, schedule = _solve("feasible_minimal", n_days=1)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=1,
    )


def test_moderator_is_own_supervisor_is_scheduled_validly():
    scenario, schedule = _solve("moderator_is_own_supervisor", n_days=1)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=1,
    )


def test_shared_supervisor_forces_split_across_days():
    # p1 and p2 share supervisor Bob Jones and there's only one session per day, so
    # they cannot share a day. Carol White (p1's s2) is unavailable on day 2, which
    # pins p1 to day 1 and, transitively, p2 to day 2 - a fully deterministic answer.
    scenario, schedule = _solve("shared_supervisor_forces_split", n_days=2)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=2,
    )
    assert schedule.loc["p1", "day"] == 1
    assert schedule.loc["p1", "session"] == 1
    assert schedule.loc["p2", "day"] == 2
    assert schedule.loc["p2", "session"] == 1


def test_unavailable_all_day_is_never_scheduled_that_day():
    scenario, schedule = _solve("unavailable_all_day", n_days=2)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=2,
    )
    assert schedule.loc["p1", "day"] == 2


def test_unavailable_session_every_day_is_forced_to_the_other_session():
    scenario, schedule = _solve("unavailable_session_every_day", n_days=1)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=1,
    )
    assert schedule.loc["p1", "day"] == 1
    assert schedule.loc["p1", "session"] == 2


def test_unavailable_specific_slot_is_forced_to_the_remaining_slot():
    scenario, schedule = _solve("unavailable_specific_slot", n_days=2)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=2,
    )
    assert schedule.loc["p1", "day"] == 2
    assert schedule.loc["p1", "session"] == 1


def test_unavailable_entire_conference_is_infeasible():
    scenario = load_scenario("unavailable_entire_conference")

    with pytest.raises(SchedulingError):
        Schedule(
            scenario.presentations,
            scenario.unavailability,
            scenario.session_times,
            n_days=1,
        ).solve()


def test_insufficient_capacity_is_infeasible():
    scenario = load_scenario("insufficient_capacity")

    with pytest.raises(SchedulingError):
        Schedule(
            scenario.presentations,
            scenario.unavailability,
            scenario.session_times,
            n_days=1,
        ).solve()


def test_unlimited_parallel_rooms_share_a_single_slot():
    # Three presentations sharing no people at all, but only one (day, session) slot
    # exists in total. Since rooms are unlimited, the only valid schedule places all
    # three in that same slot.
    scenario, schedule = _solve("parallel_rooms_unbounded", n_days=1)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=1,
    )
    assert (schedule["day"] == 1).all()
    assert (schedule["session"] == 1).all()
    assert len(schedule) == 3


def test_supervisor_is_grouped_into_fewest_possible_days():
    # Nora Chen moderates p1-p4, Omar Reyes moderates p5-p8; they share one
    # supervisor (Priya Shah, on p1 and p5), which is just enough cross-
    # contention that a non-optimizing solver can end up interleaving the two
    # moderators across 3-4 of the 4 available days instead of cleanly giving
    # each their own 2 days (the fewest possible at 2 sessions/day for 4
    # presentations each) - this reproduces the fragmentation the objective is
    # meant to fix, rather than relying on incidental solver ordering.
    scenario, schedule = _solve("grouped_into_fewest_days", n_days=4)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=4,
    )
    nora_ids = ["p1", "p2", "p3", "p4"]
    omar_ids = ["p5", "p6", "p7", "p8"]
    assert schedule.loc[nora_ids, "day"].nunique() == 2
    assert schedule.loc[omar_ids, "day"].nunique() == 2


def test_few_presentations_are_scheduled_back_to_back():
    # Eve Davis moderates p1-p3, Frank Ito moderates p4-p6; each of Eve's
    # presentations shares its supervisor with one of Frank's (Priya Shah,
    # Quentin Ross, Rosa Diaz), which is enough cross-contention that a non-
    # optimizing solver can scatter Eve across sessions 1, 3, 4 (spread 3)
    # instead of packing everyone tightly enough to leave her a contiguous
    # block (spread 2, the minimum for 3 presentations). There's only one day,
    # so active-days can't be optimized here - this isolates the secondary
    # (spread) objective.
    scenario, schedule = _solve("few_presentations_back_to_back", n_days=1)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=1,
    )
    eve_ids = ["p1", "p2", "p3"]
    sessions = schedule.loc[eve_ids, "session"]
    assert sessions.max() - sessions.min() == len(eve_ids) - 1


def test_large_synthetic_dataset_produces_a_valid_schedule():
    # Scale smoke-test over the ~290-presentation generated fixture, which has only 6
    # moderators (one chairs up to ~53 presentations). n_days=10 (80 slots at 8
    # sessions/day) gives that bottleneck moderator enough room; unavailable.csv's
    # day-only/specific-slot rules only ever reference days 1-7, so days 8-10 are
    # simply unrestricted extra capacity, not a change to the constraints themselves.
    scenario, schedule = _solve("large_synthetic", n_days=10)

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=10,
    )


def test_optimize_grouping_false_skips_the_objective_and_solves_fast():
    # several_competing_moderators is deliberately hard to *optimally* group (4
    # moderators, each pairwise sharing a supervisor with the next) - with the
    # objective on, solve() uses most of the default 30s budget just improving
    # the grouping. With it off, solve() goes back to stopping at the first
    # feasible schedule, finishing in a small fraction of a second instead.
    scenario = load_scenario("several_competing_moderators")

    start = time.perf_counter()
    schedule = Schedule(
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=6,
        optimize_grouping=False,
    ).solve()
    elapsed = time.perf_counter() - start

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=6,
    )
    assert elapsed < FAST_SOLVE_CEILING_SECONDS


def test_max_solve_seconds_bounds_the_search_time():
    # Same fixture as above: with the default 30s budget, solve() (grouping on)
    # runs the full budget trying to improve the grouping. A tiny explicit budget
    # should still return a valid (if not well-grouped) schedule promptly,
    # proving max_solve_seconds is actually threaded through to CP-SAT rather
    # than the objective ignoring it.
    scenario = load_scenario("several_competing_moderators")

    start = time.perf_counter()
    schedule = Schedule(
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=6,
        max_solve_seconds=1.0,
    ).solve()
    elapsed = time.perf_counter() - start

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=6,
    )
    assert elapsed < FAST_SOLVE_CEILING_SECONDS


def test_spread_weight_can_be_prioritized_over_active_days():
    # Same fixture/scenario as test_supervisor_is_grouped_into_fewest_possible_days,
    # where default weights land Nora on 2 active days. Inverting the weights so
    # spread dominates instead makes the solver prefer spreading her 4
    # presentations one-per-day across all 4 available days - spread 0 on every
    # active day, unbeatable - even though that means more active days, proving
    # the weights are genuinely wired into the objective, not just accepted and
    # ignored.
    scenario = load_scenario("grouped_into_fewest_days")

    schedule = Schedule(
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=4,
        active_day_weight=1,
        spread_weight=1000,
    ).solve()

    assert_valid_schedule(
        schedule,
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=4,
    )
    nora_ids = ["p1", "p2", "p3", "p4"]
    assert schedule.loc[nora_ids, "day"].nunique() == 4

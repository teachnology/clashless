import pytest

from clashless import Schedule, SchedulingError
from conftest import assert_valid_schedule, load_scenario


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

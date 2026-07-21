from conftest import DATA_DIR

from clashless import Unavailability


def test_day_only_restriction_blocks_every_session_that_day():
    unavailability = Unavailability(
        DATA_DIR / "unavailable_all_day" / "unavailable.csv"
    )

    assert unavailability.is_unavailable("Bob Jones", day=1, session=1)
    assert unavailability.is_unavailable("Bob Jones", day=1, session=2)
    assert not unavailability.is_unavailable("Bob Jones", day=2, session=1)
    assert not unavailability.is_unavailable("Bob Jones", day=2, session=2)


def test_session_only_restriction_blocks_that_session_every_day():
    unavailability = Unavailability(
        DATA_DIR / "unavailable_session_every_day" / "unavailable.csv"
    )

    assert unavailability.is_unavailable("Bob Jones", day=1, session=1)
    assert unavailability.is_unavailable("Bob Jones", day=2, session=1)
    assert not unavailability.is_unavailable("Bob Jones", day=1, session=2)
    assert not unavailability.is_unavailable("Bob Jones", day=2, session=2)


def test_specific_slot_restriction_blocks_only_that_slot():
    unavailability = Unavailability(
        DATA_DIR / "unavailable_specific_slot" / "unavailable.csv"
    )

    assert unavailability.is_unavailable("Bob Jones", day=1, session=1)
    assert not unavailability.is_unavailable("Bob Jones", day=1, session=2)
    assert not unavailability.is_unavailable("Bob Jones", day=2, session=1)


def test_global_restriction_blocks_the_entire_conference():
    unavailability = Unavailability(
        DATA_DIR / "unavailable_entire_conference" / "unavailable.csv"
    )

    assert unavailability.is_unavailable("Bob Jones", day=1, session=1)
    assert unavailability.is_unavailable("Bob Jones", day=99, session=99)


def test_person_with_no_restrictions_is_always_available():
    unavailability = Unavailability(DATA_DIR / "feasible_minimal" / "unavailable.csv")

    assert not unavailability.is_unavailable("Alice Smith", day=1, session=1)


def test_multiple_rules_for_the_same_person_all_apply():
    # Bob Jones has two rules here: unavailable all day on day 1, and unavailable
    # specifically at day=2, session=1. Both must be honoured, not just the last one.
    unavailability = Unavailability(
        DATA_DIR / "unavailable_multiple_rules" / "unavailable.csv"
    )

    assert unavailability.is_unavailable("Bob Jones", day=1, session=1)
    assert unavailability.is_unavailable("Bob Jones", day=1, session=2)
    assert unavailability.is_unavailable("Bob Jones", day=2, session=1)
    assert not unavailability.is_unavailable("Bob Jones", day=2, session=2)

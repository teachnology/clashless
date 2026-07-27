import clashless as cl


def test_day_only_restriction_blocks_every_slot_that_day():
    unavailability = cl.Unavailability({"Bob Jones": [(1, None)]})

    assert unavailability.is_unavailable("Bob Jones", day=1, slot=1)
    assert unavailability.is_unavailable("Bob Jones", day=1, slot=2)
    assert not unavailability.is_unavailable("Bob Jones", day=2, slot=1)
    assert not unavailability.is_unavailable("Bob Jones", day=2, slot=2)


def test_slot_only_restriction_blocks_that_slot_every_day():
    unavailability = cl.Unavailability({"Bob Jones": [(None, 1)]})

    assert unavailability.is_unavailable("Bob Jones", day=1, slot=1)
    assert unavailability.is_unavailable("Bob Jones", day=2, slot=1)
    assert not unavailability.is_unavailable("Bob Jones", day=1, slot=2)
    assert not unavailability.is_unavailable("Bob Jones", day=2, slot=2)


def test_specific_slot_restriction_blocks_only_that_slot():
    unavailability = cl.Unavailability({"Bob Jones": [(1, 1)]})

    assert unavailability.is_unavailable("Bob Jones", day=1, slot=1)
    assert not unavailability.is_unavailable("Bob Jones", day=1, slot=2)
    assert not unavailability.is_unavailable("Bob Jones", day=2, slot=1)


def test_global_restriction_blocks_the_entire_conference():
    unavailability = cl.Unavailability({"Bob Jones": [(None, None)]})

    assert unavailability.is_unavailable("Bob Jones", day=1, slot=1)
    assert unavailability.is_unavailable("Bob Jones", day=99, slot=99)


def test_person_with_no_restrictions_is_always_available():
    unavailability = cl.Unavailability({"Bob Jones": [(1, 1)]})

    assert not unavailability.is_unavailable("Alice Smith", day=1, slot=1)


def test_multiple_rules_for_the_same_person_all_apply():
    # Bob Jones has two rules here: unavailable all day on day 1, and unavailable
    # specifically at day=2, slot=1. Both must be honoured, not just the last one.
    unavailability = cl.Unavailability({"Bob Jones": [(1, None), (2, 1)]})

    assert unavailability.is_unavailable("Bob Jones", day=1, slot=1)
    assert unavailability.is_unavailable("Bob Jones", day=1, slot=2)
    assert unavailability.is_unavailable("Bob Jones", day=2, slot=1)
    assert not unavailability.is_unavailable("Bob Jones", day=2, slot=2)


def test_person_with_no_rules_at_all_is_always_available():
    unavailability = cl.Unavailability({})

    assert not unavailability.is_unavailable("Bob Jones", day=1, slot=1)

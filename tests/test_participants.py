import pytest

import clashless as cl


def test_loads_valid_participants():
    participants = cl.Participants(
        {"p1": ["Alice", "Bob", "Carol"], "p2": ["Dave", "Eve"]}
    )

    assert participants.data == {
        "p1": ["Alice", "Bob", "Carol"],
        "p2": ["Dave", "Eve"],
    }


def test_single_participant_is_accepted():
    participants = cl.Participants({"p1": ["Alice"]})

    assert participants.data == {"p1": ["Alice"]}


def test_empty_participant_list_is_rejected():
    with pytest.raises(ValueError, match="p1"):
        cl.Participants({"p1": []})


def test_duplicate_participant_within_one_presentation_is_rejected():
    with pytest.raises(ValueError, match="p1"):
        cl.Participants({"p1": ["Alice", "Bob", "Alice"]})


def test_same_participant_across_different_presentations_is_accepted():
    participants = cl.Participants({"p1": ["Alice", "Bob"], "p2": ["Alice", "Carol"]})

    assert participants.data == {"p1": ["Alice", "Bob"], "p2": ["Alice", "Carol"]}

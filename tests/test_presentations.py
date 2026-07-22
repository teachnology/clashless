from conftest import DATA_DIR, read_presentations

import clashless as cl


def test_loads_valid_presentations():
    presentations = cl.Presentations(
        read_presentations(DATA_DIR / "feasible_minimal" / "presentations.csv")
    )

    assert list(presentations.data.index) == ["p1", "p2"]
    assert list(presentations.data.columns) == [
        "participant_1",
        "participant_2",
        "participant_3",
        "chair",
    ]


def test_repeats_within_a_presentation_are_accepted():
    # The four roles are fully symmetric - the same person may hold two roles
    # within their own presentation (e.g. a participant chairing their own
    # session) without being rejected as a duplicate.
    presentations = cl.Presentations(
        read_presentations(
            DATA_DIR / "moderator_is_own_supervisor" / "presentations.csv"
        )
    )

    row = presentations.data.loc["p1"]
    assert row["chair"] == row["participant_2"]

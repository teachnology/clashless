import pytest

from clashless import Presentations
from conftest import DATA_DIR


def test_loads_valid_presentations():
    presentations = Presentations(DATA_DIR / "feasible_minimal" / "presentations.csv")

    assert list(presentations.data.index) == ["p1", "p2"]
    assert list(presentations.data.columns) == [
        "student",
        "s1_name",
        "s2_name",
        "moderator",
    ]


def test_moderator_may_equal_a_supervisor():
    # A supervisor chairing their own presentation (moderator == s1_name) must be
    # accepted, not rejected as a duplicate-name error.
    presentations = Presentations(
        DATA_DIR / "moderator_is_own_supervisor" / "presentations.csv"
    )

    row = presentations.data.loc["p1"]
    assert row["moderator"] == row["s1_name"]


def test_rejects_duplicate_student_names():
    with pytest.raises(ValueError):
        Presentations(DATA_DIR / "invalid_duplicate_student" / "presentations.csv")


def test_rejects_same_supervisor_for_both_slots():
    with pytest.raises(ValueError):
        Presentations(DATA_DIR / "invalid_same_supervisor" / "presentations.csv")


def test_rejects_student_supervising_themselves():
    with pytest.raises(ValueError):
        Presentations(DATA_DIR / "invalid_self_supervision" / "presentations.csv")

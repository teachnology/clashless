import pandas as pd
import pytest

import clashless as cl


def test_presentations_accepts_a_dataframe_already_indexed_by_id():
    frame = pd.DataFrame(
        {
            "participant_1": ["Alice"],
            "participant_2": ["Bob"],
            "participant_3": ["Carol"],
            "chair": ["Dave"],
        },
        index=pd.Index(["p1"], name="id"),
    )

    presentations = cl.Presentations(frame)

    assert list(presentations.data.index) == ["p1"]


def test_presentations_accepts_any_index_name():
    # The index doesn't have to be named "id" at all - only that it's unique.
    frame = pd.DataFrame(
        {
            "participant_1": ["Alice"],
            "participant_2": ["Bob"],
            "participant_3": ["Carol"],
            "chair": ["Dave"],
        },
        index=pd.Index(["p1"], name="presentation_id"),
    )

    presentations = cl.Presentations(frame)

    assert list(presentations.data.index) == ["p1"]


def test_presentations_accepts_a_column_mapping_for_role_columns():
    frame = pd.DataFrame(
        {
            "student": ["Alice"],
            "supervisor_1": ["Bob"],
            "supervisor_2": ["Carol"],
            "moderator": ["Dave"],
        },
        index=pd.Index(["p1"], name="id"),
    )

    presentations = cl.Presentations(
        frame,
        columns={
            "student": "participant_1",
            "supervisor_1": "participant_2",
            "supervisor_2": "participant_3",
            "moderator": "chair",
        },
    )

    assert list(presentations.data.columns) == [
        "participant_1",
        "participant_2",
        "participant_3",
        "chair",
    ]
    assert presentations.data.loc["p1", "chair"] == "Dave"


def test_presentations_rejects_a_non_unique_index():
    frame = pd.DataFrame(
        {
            "participant_1": ["Alice", "Eve"],
            "participant_2": ["Bob", "Frank"],
            "participant_3": ["Carol", "Grace"],
            "chair": ["Dave", "Ivy"],
        },
        index=pd.Index(["p1", "p1"], name="id"),
    )

    with pytest.raises(ValueError):
        cl.Presentations(frame)


def test_session_times_accepts_a_series():
    series = pd.Series(
        ["09:00", "11:00"], index=pd.Index([1, 2], name="session"), name="start_time"
    )

    session_times = cl.SessionTimes(series)

    assert len(session_times) == 2
    assert session_times.data.loc[1, "start_time"] == "09:00"


def test_session_times_accepts_a_series_with_a_column_mapping():
    series = pd.Series(
        ["09:00", "11:00"], index=pd.Index([1, 2], name="slot"), name="time"
    )

    session_times = cl.SessionTimes(
        series, columns={"slot": "session", "time": "start_time"}
    )

    assert len(session_times) == 2


def test_session_times_rejects_a_non_unique_index():
    series = pd.Series(
        ["09:00", "11:00"], index=pd.Index([1, 1], name="session"), name="start_time"
    )

    with pytest.raises(ValueError):
        cl.SessionTimes(series)


def test_unavailability_accepts_a_dataframe():
    frame = pd.DataFrame({"person": ["Alice"], "day": [1], "session": [None]})

    unavailability = cl.Unavailability(frame)

    assert unavailability.is_unavailable("Alice", day=1, session=1)
    assert not unavailability.is_unavailable("Alice", day=2, session=1)


def test_unavailability_accepts_a_column_mapping():
    frame = pd.DataFrame({"name": ["Alice"], "day": [1], "session": [None]})

    unavailability = cl.Unavailability(frame, columns={"name": "person"})

    assert unavailability.is_unavailable("Alice", day=1, session=1)

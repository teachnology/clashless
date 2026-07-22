import pandas as pd

from clashless import Presentations, SessionTimes, Unavailability


def test_presentations_accepts_a_dataframe_with_id_as_a_plain_column():
    frame = pd.DataFrame(
        {
            "id": ["p1", "p2"],
            "participant_1": ["Alice", "Eve"],
            "participant_2": ["Bob", "Frank"],
            "participant_3": ["Carol", "Grace"],
            "chair": ["Dave", "Ivy"],
        }
    )

    presentations = Presentations(frame)

    assert list(presentations.data.index) == ["p1", "p2"]
    assert presentations.data.loc["p1", "chair"] == "Dave"


def test_presentations_accepts_a_dataframe_with_id_already_as_the_index():
    frame = pd.DataFrame(
        {
            "participant_1": ["Alice"],
            "participant_2": ["Bob"],
            "participant_3": ["Carol"],
            "chair": ["Dave"],
        },
        index=pd.Index(["p1"], name="id"),
    )

    presentations = Presentations(frame)

    assert list(presentations.data.index) == ["p1"]


def test_presentations_accepts_a_column_mapping():
    frame = pd.DataFrame(
        {
            "presentation_id": ["p1"],
            "student": ["Alice"],
            "supervisor_1": ["Bob"],
            "supervisor_2": ["Carol"],
            "moderator": ["Dave"],
        }
    )

    presentations = Presentations(
        frame,
        columns={
            "presentation_id": "id",
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


def test_session_times_accepts_a_series():
    series = pd.Series(
        ["09:00", "11:00"], index=pd.Index([1, 2], name="session"), name="start_time"
    )

    session_times = SessionTimes(series)

    assert session_times.n_sessions == 2
    assert session_times.data.loc[1, "start_time"] == "09:00"


def test_session_times_accepts_a_series_with_a_column_mapping():
    series = pd.Series(
        ["09:00", "11:00"], index=pd.Index([1, 2], name="slot"), name="time"
    )

    session_times = SessionTimes(
        series, columns={"slot": "session", "time": "start_time"}
    )

    assert session_times.n_sessions == 2


def test_unavailability_accepts_a_dataframe():
    frame = pd.DataFrame({"person": ["Alice"], "day": [1], "session": [None]})

    unavailability = Unavailability(frame)

    assert unavailability.is_unavailable("Alice", day=1, session=1)
    assert not unavailability.is_unavailable("Alice", day=2, session=1)


def test_unavailability_accepts_a_column_mapping():
    frame = pd.DataFrame({"name": ["Alice"], "day": [1], "session": [None]})

    unavailability = Unavailability(frame, columns={"name": "person"})

    assert unavailability.is_unavailable("Alice", day=1, session=1)

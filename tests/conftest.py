import pathlib

import pandas as pd

import clashless as cl

DATA_DIR = pathlib.Path(__file__).parent / "data"


def read_presentations(path):
    return pd.read_csv(path, index_col=0)


def read_session_times(path):
    return pd.read_csv(path, index_col="session")


def read_unavailable(path):
    return pd.read_csv(path, dtype={"day": "Int64", "session": "Int64"})


class Scenario:
    """Loads whichever of presentations/unavailable/session-start-times CSVs exist
    under tests/data/<name>/, leaving the rest as None."""

    def __init__(self, name: str):
        directory = DATA_DIR / name

        presentations_path = directory / "presentations.csv"
        unavailable_path = directory / "unavailable.csv"
        session_times_path = directory / "session-start-times.csv"

        self.presentations = (
            cl.Presentations(read_presentations(presentations_path))
            if presentations_path.exists()
            else None
        )
        self.unavailability = (
            cl.Unavailability(read_unavailable(unavailable_path))
            if unavailable_path.exists()
            else None
        )
        self.session_times = (
            cl.SessionTimes(read_session_times(session_times_path))
            if session_times_path.exists()
            else None
        )


def load_scenario(name: str) -> Scenario:
    return Scenario(name)


def assert_valid_schedule(
    schedule, presentations, unavailability, session_times, n_days
):
    """Assert `schedule` satisfies every hard constraint Schedule.solve() must uphold:
    every presentation scheduled exactly once within range, nobody double-booked
    across roles at the same (day, session), and no unavailability rule violated.
    Does NOT check optimality (there is none to check yet) and does NOT forbid
    multiple presentations from sharing a (day, session) slot, since parallel rooms
    are unlimited."""
    n_sessions = len(session_times)

    assert schedule.index.is_unique
    assert set(schedule.index) == set(presentations.data.index)
    assert schedule["day"].between(1, n_days).all()
    assert schedule["session"].between(1, n_sessions).all()
    assert cl.isvalid.check_schedule(schedule, presentations, unavailability)

import pathlib

import pandas as pd

import clashless as cl

DATA_DIR = pathlib.Path(__file__).parent / "data"


def read_participants(path):
    df = pd.read_csv(path)
    return {
        presentation_id: list(group["participant"])
        for presentation_id, group in df.groupby("id", sort=False)
    }


def read_sessions(path):
    return pd.read_csv(path, index_col="id")["session"].to_dict()


def read_unavailable(path):
    df = pd.read_csv(path, dtype={"day": "Int64", "slot": "Int64"})
    rules = {}
    for person, group in df.groupby("person", sort=False):
        rules[person] = [
            (None if pd.isna(day) else int(day), None if pd.isna(slot) else int(slot))
            for day, slot in zip(group["day"], group["slot"], strict=True)
        ]
    return rules


class Scenario:
    """Loads whichever of participants/sessions/unavailable CSVs exist under
    tests/data/<name>/, leaving the rest as None."""

    def __init__(self, name: str):
        directory = DATA_DIR / name

        participants_path = directory / "participants.csv"
        sessions_path = directory / "sessions.csv"
        unavailable_path = directory / "unavailable.csv"

        self.participants = (
            cl.Participants(read_participants(participants_path))
            if participants_path.exists()
            else None
        )
        self.sessions = (
            cl.Sessions(read_sessions(sessions_path))
            if sessions_path.exists()
            else None
        )
        self.unavailability = (
            cl.Unavailability(read_unavailable(unavailable_path))
            if unavailable_path.exists()
            else None
        )


def load_scenario(name: str) -> Scenario:
    return Scenario(name)


def assert_valid_schedule(  # noqa: PLR0917
    schedule, participants, sessions, unavailability, n_days, n_slots
):
    """Assert `schedule` satisfies every hard constraint Schedule.solve() must uphold:
    every presentation scheduled exactly once within range, nobody double-booked
    across presentations at the same (day, slot), no two presentations sharing a
    session at the same (day, slot), and no unavailability rule violated. Does NOT
    check optimality (there is none to check yet) and does NOT forbid multiple
    presentations from sharing a (day, slot), since parallel rooms are unlimited."""
    assert set(schedule) == set(participants.data)
    assert all(1 <= entry["day"] <= n_days for entry in schedule.values())
    assert all(1 <= entry["slot"] <= n_slots for entry in schedule.values())
    assert cl.isvalid.schedule(schedule, participants, sessions, unavailability)

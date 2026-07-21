import pathlib

from clashless import Presentations, SessionTimes, Unavailability

DATA_DIR = pathlib.Path(__file__).parent / "data"

ROLE_COLUMNS = ["student", "s1_name", "s2_name", "moderator"]


class Scenario:
    """Loads whichever of presentations/unavailable/session-start-times CSVs exist
    under tests/data/<name>/, leaving the rest as None."""

    def __init__(self, name: str):
        directory = DATA_DIR / name

        presentations_path = directory / "presentations.csv"
        unavailable_path = directory / "unavailable.csv"
        session_times_path = directory / "session-start-times.csv"

        self.presentations = (
            Presentations(presentations_path) if presentations_path.exists() else None
        )
        self.unavailability = (
            Unavailability(unavailable_path) if unavailable_path.exists() else None
        )
        self.session_times = (
            SessionTimes(session_times_path) if session_times_path.exists() else None
        )


def load_scenario(name: str) -> Scenario:
    return Scenario(name)


def assert_valid_schedule(schedule, presentations, unavailability, session_times, n_days):
    """Assert `schedule` satisfies every hard constraint Schedule.solve() must uphold:
    every presentation scheduled exactly once within range, nobody double-booked across
    roles at the same (day, session), and no unavailability rule violated. Does NOT check
    optimality (there is none to check yet) and does NOT forbid multiple presentations
    from sharing a (day, session) slot, since parallel rooms are unlimited."""
    data = presentations.data
    n_sessions = session_times.n_sessions

    assert schedule.index.is_unique
    assert set(schedule.index) == set(data.index)
    assert schedule["day"].between(1, n_days).all()
    assert schedule["session"].between(1, n_sessions).all()

    for (day, session), group in schedule.groupby(["day", "session"]):
        people_in_slot = []
        for presentation_id in group.index:
            row = data.loc[presentation_id]
            # A person may hold two roles within their OWN presentation (e.g. a
            # supervisor chairing their own session) - that's not a clash. Dedupe
            # per presentation before checking for clashes against OTHER presentations.
            presentation_people = set(row[ROLE_COLUMNS])
            for person in presentation_people:
                assert not unavailability.is_unavailable(person, day, session), (
                    f"{person} is unavailable at day={day}, session={session} but "
                    f"presentation {presentation_id} is scheduled there"
                )
            people_in_slot.extend(presentation_people)
        assert len(people_in_slot) == len(set(people_in_slot)), (
            f"someone is double-booked at day={day}, session={session}: {people_in_slot}"
        )

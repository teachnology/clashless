import pandas as pd

from clashless._io import load_table


class Unavailability:
    """Loads unavailable.csv, or an equivalent in-memory `pd.DataFrame`, and
    answers is_unavailable(person, day, session) queries.

    `source` may be a CSV path or a DataFrame with `person`, nullable `day`,
    and nullable `session` columns. `columns`, if given, maps your own column
    names to those three.

    A row's nullable day/session act as wildcards:
      - day set, session null   -> unavailable the whole day
      - day null, session set   -> unavailable that session, every day
      - both set                -> unavailable for that specific slot only
      - both null                -> unavailable for the entire conference
    """

    def __init__(self, source, columns=None):
        self.data = load_table(source, columns).astype(
            {"day": "Int64", "session": "Int64"}
        )
        self._rules_by_person = {
            person: list(zip(rows["day"], rows["session"]))
            for person, rows in self.data.groupby("person")
        }

    def is_unavailable(self, person, day, session):
        for rule_day, rule_session in self._rules_by_person.get(person, []):
            day_matches = pd.isna(rule_day) or rule_day == day
            session_matches = pd.isna(rule_session) or rule_session == session
            if day_matches and session_matches:
                return True
        return False

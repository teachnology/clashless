from clashless._io import load_table


class SessionTimes:
    """Loads session-start-times.csv, or an equivalent in-memory
    `pd.DataFrame`/`pd.Series`; the same sessions apply every conference day.

    `source` may be a CSV path, a DataFrame, or a Series indexed by session
    number (its natural shape, being a single `start_time` value per
    session). `columns`, if given, maps your own column/index names to the
    ones clashless expects (`session`, `start_time`).
    """

    def __init__(self, source, columns=None):
        self.data = load_table(source, columns).set_index("session")

    @property
    def n_sessions(self):
        return len(self.data)

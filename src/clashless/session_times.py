import pandas as pd


class SessionTimes:
    """Loads session-start-times.csv. The same sessions apply on every conference day."""

    def __init__(self, path):
        self.data = pd.read_csv(path, index_col="session")

    @property
    def n_sessions(self):
        return len(self.data)

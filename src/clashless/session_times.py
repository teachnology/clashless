import pandas as pd


class SessionTimes:
    """Wrap a session-times table; the same sessions apply every conference day.

    `source` is a `pd.DataFrame` or a `pd.Series` (its natural single-column
    shape, being one `start_time` value per session), already indexed by
    session number - the index is taken as-is, whatever it's named, and must
    be unique (a `ValueError` is raised otherwise). `columns`, if given, maps
    your own column name to the one clashless expects (`start_time`).
    """

    def __init__(self, source, columns=None):
        data = source.to_frame() if isinstance(source, pd.Series) else source.copy()
        if columns:
            data = data.rename(columns=columns)

        if not data.index.is_unique:
            raise ValueError("Session numbers must be unique.")

        self.data = data

    def __len__(self):
        """Return the number of sessions per day."""
        return len(self.data)

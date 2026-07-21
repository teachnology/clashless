import pandas as pd

ROLE_COLUMNS = ["student", "s1_name", "s2_name", "moderator"]


class Presentations:
    """Loads and validates presentations.csv.

    A presentation's moderator may be one of its own supervisors (a supervisor
    chairing their own session) - that is not a validation error.
    """

    def __init__(self, path):
        data = pd.read_csv(path, index_col="id")
        self._validate(data)
        self.data = data

    @staticmethod
    def _validate(data):
        if not data["student"].is_unique:
            raise ValueError("student names must be unique")
        if (data["s1_name"] == data["s2_name"]).any():
            raise ValueError("s1_name and s2_name must differ for every presentation")
        if (data["student"] == data["s1_name"]).any() or (
            data["student"] == data["s2_name"]
        ).any():
            raise ValueError("a student cannot be their own supervisor")

ROLE_COLUMNS = ["participant_1", "participant_2", "participant_3", "chair"]


class Presentations:
    """Wraps a presentations table.

    `source` is a `pd.DataFrame` already indexed by presentation id - the
    index is taken as-is, whatever it's named, and must be unique (a
    `ValueError` is raised otherwise). `columns`, if given, maps your own
    role-column names to the ones clashless expects (`participant_1`,
    `participant_2`, `participant_3`, `chair`) - e.g.
    `columns={"student": "participant_1"}` - so you don't have to rename your
    own data by hand first.

    Every presentation has four symmetric roles: `participant_1`,
    `participant_2`, `participant_3`, and `chair`. No role is special and
    nothing about repetition is enforced - the same person may appear in more
    than one role, including more than once within the same presentation's
    own row (e.g. a participant chairing their own session). Use
    `clashless.isvalid.report` to see a summary of whatever repetition your
    data actually has.
    """

    def __init__(self, source, columns=None):
        data = source.copy()
        if columns:
            data = data.rename(columns=columns)

        if not data.index.is_unique:
            raise ValueError("Presentation ids must be unique.")

        self.data = data

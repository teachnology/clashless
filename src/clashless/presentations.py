from clashless._io import load_table

ROLE_COLUMNS = ["participant_1", "participant_2", "participant_3", "chair"]


class Presentations:
    """Loads presentations.csv, or an equivalent in-memory `pd.DataFrame`.

    `source` may be a CSV path, an existing DataFrame, or (as a path) anything
    `pandas.read_csv` accepts. `columns`, if given, maps your own column names
    to the ones clashless expects (`id`, `participant_1`, `participant_2`,
    `participant_3`, `chair`) - e.g. `columns={"student": "participant_1"}` -
    so you don't have to rename your own data by hand first.

    Every presentation has four symmetric roles: `participant_1`,
    `participant_2`, `participant_3`, and `chair`. No role is special and
    nothing about repetition is enforced - the same person may appear in more
    than one role, including more than once within the same presentation's
    own row (e.g. a participant chairing their own session). Use
    `clashless.isvalid.report` to see a summary of whatever repetition your
    data actually has.
    """

    def __init__(self, source, columns=None):
        data = load_table(source, columns).set_index("id")
        self.data = data

import pandas as pd


def load_table(source, columns=None):
    """Return `source` as a plain DataFrame, ready for a class-specific
    index/dtype step. `source` may be a CSV path, an existing DataFrame, or a
    Series (only meaningful for a naturally single-column table, e.g.
    SessionTimes). `columns`, if given, maps the caller's own column names to
    the ones clashless expects, applied before any index is set - so it can
    rename the identifying column (e.g. id/session) too, not just data
    columns.
    """
    if isinstance(source, pd.Series):
        data = source.reset_index()
    elif isinstance(source, pd.DataFrame):
        data = source.reset_index() if source.index.name else source.copy()
    else:
        data = pd.read_csv(source)

    if columns:
        data = data.rename(columns=columns)
    return data

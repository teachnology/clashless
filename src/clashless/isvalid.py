import itertools

import pandas as pd

from clashless.presentations import ROLE_COLUMNS

TOP_N_MOST_FREQUENT = 10


def report(presentations):
    """Print a short, human-facing report on repetition across a
    Presentations table: nothing here is enforced by `Presentations` itself
    (the four roles are fully symmetric), so this is purely informational -
    it never raises.

    Covers, for the four role columns (participant_1, participant_2,
    participant_3, chair): how unique each column is, how often the same
    person holds two roles within one presentation's own row, and who
    appears most often overall.
    """
    data = presentations.data
    n_rows = len(data)
    lines = ["Presentation role repetition report", f"Rows: {n_rows}", ""]

    lines.append("Per-column uniqueness:")
    for column in ROLE_COLUMNS:
        n_unique = data[column].nunique()
        lines.append(
            f"  {column}: {n_unique} unique / {n_rows} rows "
            f"({n_rows - n_unique} repeated)"
        )
    lines.append("")

    lines.append("Repeats within the same presentation (same person, same row):")
    rows_with_any_repeat = pd.Series(False, index=data.index)
    for left, right in itertools.combinations(ROLE_COLUMNS, 2):
        matches = data[left] == data[right]
        rows_with_any_repeat |= matches
        lines.append(f"  {left} == {right}: {matches.sum()} row(s)")
    lines.append(f"  rows with any within-row repeat: {rows_with_any_repeat.sum()}")
    lines.append("")

    lines.append(f"Most frequently appearing people (top {TOP_N_MOST_FREQUENT}):")
    counts = pd.concat([data[column] for column in ROLE_COLUMNS]).value_counts()
    for person, count in counts.head(TOP_N_MOST_FREQUENT).items():
        lines.append(f"  {person}: {count}")

    print("\n".join(lines))

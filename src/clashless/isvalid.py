import itertools

import pandas as pd

from clashless.presentations import ROLE_COLUMNS

TOP_N_MOST_FREQUENT = 10


def report(presentations):
    """Print a short, human-facing report on repetition across a Presentations table.

    Nothing here is enforced by `Presentations` itself (the four roles are
    fully symmetric), so this is purely informational - it never raises.

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


def check_schedule(schedule, presentations, unavailability):
    """Check `schedule` for clashes and print a short reassurance report.

    Covers double-bookings and unavailability violations, and returns `True`
    if none were found. `Schedule.solve()` already guarantees a clash-free
    result internally; this is for double-checking a schedule built or
    edited some other way.
    """
    data = presentations.data
    double_bookings = []
    unavailability_violations = []

    for (day, session), group in schedule.groupby(["day", "session"]):
        people_in_slot = []
        for presentation_id in group.index:
            # A person may hold two roles within their OWN presentation (e.g.
            # a participant chairing their own session) - that's not a clash.
            # Dedupe per presentation before checking against OTHER ones.
            presentation_people = set(data.loc[presentation_id, ROLE_COLUMNS])
            for person in presentation_people:
                if unavailability.is_unavailable(person, day, session):
                    unavailability_violations.append(
                        (person, day, session, presentation_id)
                    )
            people_in_slot.extend(presentation_people)

        seen = set()
        for person in people_in_slot:
            if person in seen:
                double_bookings.append((person, day, session))
            seen.add(person)

    lines = ["Schedule clash report", f"Presentations: {len(schedule)}", ""]
    if double_bookings:
        lines.append(f"Double-booking clashes ({len(double_bookings)}):")
        for person, day, session in double_bookings:
            lines.append(f"  {person}: day {day}, session {session}")
    if unavailability_violations:
        lines.append(f"Unavailability violations ({len(unavailability_violations)}):")
        for person, day, session, presentation_id in unavailability_violations:
            lines.append(
                f"  {person}: unavailable at day {day}, session {session} "
                f"but scheduled for {presentation_id}"
            )
    if not double_bookings and not unavailability_violations:
        lines.append("No clashes found.")

    print("\n".join(lines))
    return not double_bookings and not unavailability_violations

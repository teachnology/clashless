def _clashes_in_slot(day_slot, ids_in_slot, participants, sessions, unavailability):
    day, slot = day_slot
    double_bookings = []
    unavailability_violations = []
    session_clashes = []

    people_in_slot = []
    session_owner = {}
    for presentation_id in ids_in_slot:
        presentation_people = participants.data[presentation_id]
        for person in presentation_people:
            if unavailability.is_unavailable(person, day, slot):
                unavailability_violations.append((person, day, slot, presentation_id))
        people_in_slot.extend(presentation_people)

        session = sessions.data[presentation_id]
        if session in session_owner:
            session_clashes.append(
                (session, day, slot, session_owner[session], presentation_id)
            )
        else:
            session_owner[session] = presentation_id

    seen = set()
    for person in people_in_slot:
        if person in seen:
            double_bookings.append((person, day, slot))
        seen.add(person)

    return double_bookings, unavailability_violations, session_clashes


def schedule(schedule, participants, sessions, unavailability):
    """Check `schedule` for clashes and print a short reassurance report.

    Covers double-bookings, unavailability violations, and session clashes
    (two presentations sharing a session assigned to the same day+slot), and
    returns `True` if none were found. `Schedule.solve()` already guarantees
    a clash-free result internally; this is for double-checking a schedule
    built or edited some other way.
    """
    groups = {}
    for presentation_id, entry in schedule.items():
        groups.setdefault((entry["day"], entry["slot"]), []).append(presentation_id)

    double_bookings = []
    unavailability_violations = []
    session_clashes = []
    for day_slot, ids_in_slot in groups.items():
        slot_double_bookings, slot_unavailability, slot_sessions = _clashes_in_slot(
            day_slot, ids_in_slot, participants, sessions, unavailability
        )
        double_bookings.extend(slot_double_bookings)
        unavailability_violations.extend(slot_unavailability)
        session_clashes.extend(slot_sessions)

    lines = ["Schedule clash report", f"Presentations: {len(schedule)}", ""]
    if double_bookings:
        lines.append(f"Double-booking clashes ({len(double_bookings)}):")
        for person, day, slot in double_bookings:
            lines.append(f"  {person}: day {day}, slot {slot}")
    if unavailability_violations:
        lines.append(f"Unavailability violations ({len(unavailability_violations)}):")
        for person, day, slot, presentation_id in unavailability_violations:
            lines.append(
                f"  {person}: unavailable at day {day}, slot {slot} "
                f"but scheduled for {presentation_id}"
            )
    if session_clashes:
        lines.append(f"Session clashes ({len(session_clashes)}):")
        for session, day, slot, first_id, second_id in session_clashes:
            lines.append(
                f"  session {session!r}: day {day}, slot {slot} - "
                f"{first_id} and {second_id}"
            )
    if not double_bookings and not unavailability_violations and not session_clashes:
        lines.append("No clashes found.")

    print("\n".join(lines))
    return not double_bookings and not unavailability_violations and not session_clashes

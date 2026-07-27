from conftest import load_scenario

import clashless as cl


def test_schedule_reports_no_clashes_for_a_solved_schedule(capsys):
    scenario = load_scenario("feasible_minimal")
    schedule = cl.Schedule(
        scenario.participants,
        scenario.sessions,
        scenario.unavailability,
        1,
        2,
    ).solve()

    result = cl.isvalid.schedule(
        schedule, scenario.participants, scenario.sessions, scenario.unavailability
    )

    output = capsys.readouterr().out
    assert result is True
    assert "No clashes found." in output


def test_schedule_detects_a_double_booking():
    # Alice appears in both presentations, but both are forced into the same
    # (day, slot) - a clash a valid Schedule.solve() result could never produce.
    participants = cl.Participants({"p1": ["Alice", "Bob"], "p2": ["Alice", "Carol"]})
    sessions = cl.Sessions({"p1": "A", "p2": "B"})
    unavailability = cl.Unavailability({})
    schedule = {"p1": {"day": 1, "slot": 1}, "p2": {"day": 1, "slot": 1}}

    result = cl.isvalid.schedule(schedule, participants, sessions, unavailability)

    assert result is False


def test_schedule_detects_an_unavailability_violation(capsys):
    participants = cl.Participants({"p1": ["Alice", "Bob"]})
    sessions = cl.Sessions({"p1": "A"})
    unavailability = cl.Unavailability({"Alice": [(1, 1)]})
    schedule = {"p1": {"day": 1, "slot": 1}}

    result = cl.isvalid.schedule(schedule, participants, sessions, unavailability)

    output = capsys.readouterr().out
    assert result is False
    assert "Alice: unavailable at day 1, slot 1 but scheduled for p1" in output


def test_schedule_detects_a_session_clash(capsys):
    # p1 and p2 share no people at all, but both belong to session "A" and are
    # forced into the same (day, slot) - a room can't host two presentations
    # at once even if they don't share a person.
    participants = cl.Participants({"p1": ["Alice"], "p2": ["Bob"]})
    sessions = cl.Sessions({"p1": "A", "p2": "A"})
    unavailability = cl.Unavailability({})
    schedule = {"p1": {"day": 1, "slot": 1}, "p2": {"day": 1, "slot": 1}}

    result = cl.isvalid.schedule(schedule, participants, sessions, unavailability)

    output = capsys.readouterr().out
    assert result is False
    assert "session 'A': day 1, slot 1" in output

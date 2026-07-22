import pandas as pd
from conftest import DATA_DIR, load_scenario, read_presentations

import clashless as cl


def test_report_shows_no_repeats_for_clean_data(capsys):
    presentations = cl.Presentations(
        read_presentations(DATA_DIR / "feasible_minimal" / "presentations.csv")
    )

    cl.isvalid.report(presentations)

    output = capsys.readouterr().out
    assert "rows with any within-row repeat: 0" in output


def test_report_shows_a_within_row_repeat(capsys):
    presentations = cl.Presentations(
        read_presentations(
            DATA_DIR / "moderator_is_own_supervisor" / "presentations.csv"
        )
    )
    row = presentations.data.loc["p1"]

    cl.isvalid.report(presentations)

    output = capsys.readouterr().out
    assert "participant_2 == chair: 1 row(s)" in output
    assert "rows with any within-row repeat: 1" in output
    assert row["chair"] in output


def test_check_schedule_reports_no_clashes_for_a_solved_schedule(capsys):
    scenario = load_scenario("feasible_minimal")
    schedule = cl.Schedule(
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=1,
    ).solve()

    result = cl.isvalid.check_schedule(
        schedule, scenario.presentations, scenario.unavailability
    )

    output = capsys.readouterr().out
    assert result is True
    assert "No clashes found." in output


def test_check_schedule_detects_a_double_booking(capsys):
    # Alice appears as participant_1 in both presentations, but both are
    # forced into the same (day, session) - a clash a valid Schedule.solve()
    # result could never produce.
    presentations = cl.Presentations(
        pd.DataFrame(
            {
                "participant_1": ["Alice", "Alice"],
                "participant_2": ["Bob", "Eve"],
                "participant_3": ["Carol", "Frank"],
                "chair": ["Dave", "Grace"],
            },
            index=pd.Index(["p1", "p2"], name="id"),
        )
    )
    unavailability = cl.Unavailability(
        pd.DataFrame({"person": [], "day": [], "session": []})
    )
    schedule = pd.DataFrame(
        {"day": [1, 1], "session": [1, 1]}, index=pd.Index(["p1", "p2"], name="id")
    )

    result = cl.isvalid.check_schedule(schedule, presentations, unavailability)

    output = capsys.readouterr().out
    assert result is False
    assert "Alice: day 1, session 1" in output


def test_check_schedule_detects_an_unavailability_violation(capsys):
    presentations = cl.Presentations(
        pd.DataFrame(
            {
                "participant_1": ["Alice"],
                "participant_2": ["Bob"],
                "participant_3": ["Carol"],
                "chair": ["Dave"],
            },
            index=pd.Index(["p1"], name="id"),
        )
    )
    unavailability = cl.Unavailability(
        pd.DataFrame({"person": ["Alice"], "day": [1], "session": [1]})
    )
    schedule = pd.DataFrame(
        {"day": [1], "session": [1]}, index=pd.Index(["p1"], name="id")
    )

    result = cl.isvalid.check_schedule(schedule, presentations, unavailability)

    output = capsys.readouterr().out
    assert result is False
    assert "Alice: unavailable at day 1, session 1 but scheduled for p1" in output

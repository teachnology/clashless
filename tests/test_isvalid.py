from conftest import DATA_DIR

from clashless import Presentations, isvalid


def test_report_shows_no_repeats_for_clean_data(capsys):
    presentations = Presentations(DATA_DIR / "feasible_minimal" / "presentations.csv")

    isvalid.report(presentations)

    output = capsys.readouterr().out
    assert "rows with any within-row repeat: 0" in output


def test_report_shows_a_within_row_repeat(capsys):
    presentations = Presentations(
        DATA_DIR / "moderator_is_own_supervisor" / "presentations.csv"
    )
    row = presentations.data.loc["p1"]

    isvalid.report(presentations)

    output = capsys.readouterr().out
    assert "participant_2 == chair: 1 row(s)" in output
    assert "rows with any within-row repeat: 1" in output
    assert row["chair"] in output

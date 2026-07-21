from conftest import DATA_DIR

from clashless import SessionTimes


def test_n_sessions_matches_row_count():
    session_times = SessionTimes(
        DATA_DIR / "feasible_minimal" / "session-start-times.csv"
    )

    assert session_times.n_sessions == 2


def test_single_session_conference():
    session_times = SessionTimes(
        DATA_DIR / "moderator_is_own_supervisor" / "session-start-times.csv"
    )

    assert session_times.n_sessions == 1


def test_large_synthetic_has_eight_sessions_per_day():
    session_times = SessionTimes(
        DATA_DIR / "large_synthetic" / "session-start-times.csv"
    )

    assert session_times.n_sessions == 8

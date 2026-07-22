from conftest import DATA_DIR, read_session_times

import clashless as cl


def test_n_sessions_matches_row_count():
    session_times = cl.SessionTimes(
        read_session_times(DATA_DIR / "feasible_minimal" / "session-start-times.csv")
    )

    assert len(session_times) == 2


def test_single_session_conference():
    session_times = cl.SessionTimes(
        read_session_times(
            DATA_DIR / "moderator_is_own_supervisor" / "session-start-times.csv"
        )
    )

    assert len(session_times) == 1


def test_large_synthetic_has_eight_sessions_per_day():
    session_times = cl.SessionTimes(
        read_session_times(DATA_DIR / "large_synthetic" / "session-start-times.csv")
    )

    assert len(session_times) == 8

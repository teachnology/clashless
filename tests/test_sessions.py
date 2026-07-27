import clashless as cl


def test_loads_valid_sessions():
    sessions = cl.Sessions({"p1": "A", "p2": "A", "p3": "B"})

    assert sessions.data == {"p1": "A", "p2": "A", "p3": "B"}


def test_session_labels_may_be_any_hashable_value():
    sessions = cl.Sessions({"p1": 1, "p2": 1, "p3": 2})

    assert sessions.data == {"p1": 1, "p2": 1, "p3": 2}


def test_empty_sessions_is_accepted():
    sessions = cl.Sessions({})

    assert sessions.data == {}

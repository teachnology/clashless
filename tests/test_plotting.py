import math

import plotly.graph_objects as go
from conftest import load_scenario
from openpyxl import load_workbook

import clashless as cl


def _solve_parallel_rooms_unbounded():
    scenario = load_scenario("parallel_rooms_unbounded")
    schedule = cl.Schedule(
        scenario.participants,
        scenario.sessions,
        scenario.unavailability,
        1,
        1,
    ).solve()
    return scenario, schedule


def test_plot_schedule_returns_a_figure_with_one_cell_per_presentation():
    scenario, schedule = _solve_parallel_rooms_unbounded()

    fig = cl.plot_schedule(
        schedule, scenario.participants, scenario.sessions, n_days=1, n_slots=1
    )

    assert isinstance(fig, go.Figure)
    heatmap = fig.data[0]

    occupied = sum(1 for row in heatmap.z for value in row if not math.isnan(value))
    assert occupied == len(schedule)

    # all three (distinct-session) presentations should get their own column
    assert set(heatmap.x) == set(scenario.sessions.data.values())


def test_plot_schedule_labels_each_cell_with_its_presentation_id():
    scenario, schedule = _solve_parallel_rooms_unbounded()

    fig = cl.plot_schedule(
        schedule, scenario.participants, scenario.sessions, n_days=1, n_slots=1
    )
    heatmap = fig.data[0]

    labelled_ids = {value for row in heatmap.text for value in row if value}
    assert labelled_ids == set(schedule)


def test_plot_schedule_hover_includes_id_and_participants():
    scenario, schedule = _solve_parallel_rooms_unbounded()

    fig = cl.plot_schedule(
        schedule, scenario.participants, scenario.sessions, n_days=1, n_slots=1
    )
    heatmap = fig.data[0]

    presentation_id = next(iter(schedule))
    participants = scenario.participants.data[presentation_id]
    hover_entries = [value for r in heatmap.customdata for value in r if value]
    matching = [text for text in hover_entries if f"ID: {presentation_id}" in text]

    assert len(matching) == 1
    for participant in participants:
        assert participant in matching[0]


def test_plot_schedule_uses_given_slot_labels():
    scenario, schedule = _solve_parallel_rooms_unbounded()

    fig = cl.plot_schedule(
        schedule,
        scenario.participants,
        scenario.sessions,
        n_days=1,
        n_slots=1,
        slot_labels={1: "09:00"},
    )

    assert list(fig.data[0].y) == ["Day 1 · 09:00"]


def test_export_schedule_to_excel_writes_full_details_per_cell(tmp_path):
    scenario, schedule = _solve_parallel_rooms_unbounded()
    path = tmp_path / "schedule.xlsx"

    cl.export_schedule_to_excel(
        schedule,
        scenario.participants,
        scenario.sessions,
        n_days=1,
        n_slots=1,
        path=path,
    )

    workbook = load_workbook(path)
    sheet = workbook.active

    header_row = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    assert set(header_row[1:]) == set(scenario.sessions.data.values())

    filled_cells = [
        cell.value
        for row in sheet.iter_rows(min_row=2)
        for cell in row
        if cell.column > 1 and cell.value
    ]
    assert len(filled_cells) == len(schedule)

    presentation_id = next(iter(schedule))
    participants = scenario.participants.data[presentation_id]
    (matching,) = [text for text in filled_cells if f"ID: {presentation_id}" in text]
    for participant in participants:
        assert participant in matching

import math

import plotly.graph_objects as go
from conftest import load_scenario
from openpyxl import load_workbook

from clashless import Schedule, export_schedule_to_excel, plot_schedule


def _solve_parallel_rooms_unbounded():
    scenario = load_scenario("parallel_rooms_unbounded")
    schedule = Schedule(
        scenario.presentations,
        scenario.unavailability,
        scenario.session_times,
        n_days=1,
    ).solve()
    return scenario, schedule


def test_plot_schedule_returns_a_figure_with_one_cell_per_presentation():
    scenario, schedule = _solve_parallel_rooms_unbounded()

    fig = plot_schedule(schedule, scenario.presentations, scenario.session_times)

    assert isinstance(fig, go.Figure)
    heatmap = fig.data[0]

    occupied = sum(1 for row in heatmap.z for value in row if not math.isnan(value))
    assert occupied == len(schedule)

    # all three (distinct-chair) presentations should get their own column
    assert set(heatmap.x) == set(scenario.presentations.data["chair"])


def test_plot_schedule_labels_each_cell_with_its_presentation_id():
    scenario, schedule = _solve_parallel_rooms_unbounded()

    fig = plot_schedule(schedule, scenario.presentations, scenario.session_times)
    heatmap = fig.data[0]

    labelled_ids = {value for row in heatmap.text for value in row if value}
    assert labelled_ids == set(schedule.index)


def test_plot_schedule_hover_includes_id_and_participants():
    scenario, schedule = _solve_parallel_rooms_unbounded()

    fig = plot_schedule(schedule, scenario.presentations, scenario.session_times)
    heatmap = fig.data[0]

    presentation_id = schedule.index[0]
    row = scenario.presentations.data.loc[presentation_id]
    hover_entries = [value for r in heatmap.customdata for value in r if value]
    matching = [text for text in hover_entries if f"ID: {presentation_id}" in text]

    assert len(matching) == 1
    assert row["participant_1"] in matching[0]
    assert row["participant_2"] in matching[0]
    assert row["participant_3"] in matching[0]


def test_export_schedule_to_excel_writes_full_details_per_cell(tmp_path):
    scenario, schedule = _solve_parallel_rooms_unbounded()
    path = tmp_path / "schedule.xlsx"

    export_schedule_to_excel(
        schedule, scenario.presentations, scenario.session_times, path
    )

    workbook = load_workbook(path)
    sheet = workbook.active

    header_row = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    assert set(header_row[1:]) == set(scenario.presentations.data["chair"])

    filled_cells = [
        cell.value
        for row in sheet.iter_rows(min_row=2)
        for cell in row
        if cell.column > 1 and cell.value
    ]
    assert len(filled_cells) == len(schedule)

    presentation_id = schedule.index[0]
    row = scenario.presentations.data.loc[presentation_id]
    (matching,) = [text for text in filled_cells if f"ID: {presentation_id}" in text]
    assert row["participant_1"] in matching
    assert row["participant_2"] in matching
    assert row["participant_3"] in matching
    assert row["chair"] in matching

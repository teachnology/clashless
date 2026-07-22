import plotly.graph_objects as go
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Validated dataviz palette (see project's dataviz skill / palette.md). This is a
# single-series chart (occupied vs. empty slot), so only the accent hue and chart
# chrome tokens are needed - no categorical CVD comparison applies.
ACCENT_COLOR = "#2a78d6"
ACCENT_TINT = "#b7d3f6"  # sequential blue, step 150 - a spreadsheet-friendly fill
SURFACE_COLOR = "#fcfcfb"
PRIMARY_TEXT = "#0b0b0b"
MUTED_TEXT = "#898781"
AXIS_COLOR = "#c3c2b7"

FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def _format_time(value):
    # session-start-times.csv round-trips "start_time" as a plain string
    # (e.g. "09:30:00"); a real datetime.time is also accepted.
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    return str(value)[:5]


def _build_grid(schedule, presentations, session_times):
    """Lay a solved schedule out on a room x time grid.

    Shared by plot_schedule and export_schedule_to_excel so both render
    exactly the same layout. Returns the ordered room (chair) labels, the
    ordered chronological slot labels, and a slot_labels x chair_order
    matrix of per-presentation detail dicts (None where nothing is
    scheduled).
    """
    data = presentations.data
    n_sessions = len(session_times)
    start_times = session_times.data["start_time"]
    n_days = int(schedule["day"].max())

    merged = schedule.join(data)
    chair_order = merged["chair"].value_counts().index.tolist()

    def slot_label(day, session):
        return f"Day {day} · {_format_time(start_times.loc[session])}"

    slot_labels = [
        slot_label(day, session)
        for day in range(1, n_days + 1)
        for session in range(1, n_sessions + 1)
    ]
    row_index = {label: i for i, label in enumerate(slot_labels)}
    column_index = {chair: j for j, chair in enumerate(chair_order)}

    cells = [[None] * len(chair_order) for _ in slot_labels]
    for presentation_id, row in merged.iterrows():
        i = row_index[slot_label(row["day"], row["session"])]
        j = column_index[row["chair"]]
        cells[i][j] = {
            "id": presentation_id,
            "participant_1": row["participant_1"],
            "participant_2": row["participant_2"],
            "participant_3": row["participant_3"],
            "chair": row["chair"],
            "day": row["day"],
            "session": row["session"],
        }

    return chair_order, slot_labels, cells


def plot_schedule(schedule, presentations, session_times):
    """Render an interactive timetable for a solved Schedule.

    Rooms (chairs) run along the x-axis and chronological (day, session) slots
    run down the y-axis - both are positional, so they carry room/time identity
    without needing a color per chair. Each filled cell is one scheduled
    presentation in the single accent color, labelled with its presentation id;
    hovering it shows the full detail - id, participants, and chair. Empty
    cells are real gaps: a chair only owns one room for the whole day they're
    chairing, so a free slot in their column means nothing is scheduled there,
    not missing data.
    """
    chair_order, slot_labels, cells = _build_grid(
        schedule, presentations, session_times
    )

    z = [[float("nan")] * len(chair_order) for _ in slot_labels]
    id_labels = [[""] * len(chair_order) for _ in slot_labels]
    hover_text = [[""] * len(chair_order) for _ in slot_labels]

    for i, row_cells in enumerate(cells):
        for j, info in enumerate(row_cells):
            if info is None:
                continue
            z[i][j] = 1
            id_labels[i][j] = str(info["id"])
            hover_text[i][j] = (
                f"<b>ID: {info['id']}</b><br>"
                f"Participants: {info['participant_1']}, {info['participant_2']}, "
                f"{info['participant_3']}<br>"
                f"Chair: {info['chair']}<br>"
                f"Day {info['day']}, session {info['session']}"
            )

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=chair_order,
            y=slot_labels,
            text=id_labels,
            texttemplate="%{text}",
            textfont=dict(color="#ffffff", size=11, family=FONT_FAMILY),
            customdata=hover_text,
            hovertemplate="%{customdata}<extra></extra>",
            hoverongaps=False,
            colorscale=[[0, ACCENT_COLOR], [1, ACCENT_COLOR]],
            zmin=0,
            zmax=1,
            showscale=False,
            xgap=3,
            ygap=3,
        )
    )

    fig.update_layout(
        title=dict(
            text=(
                "Conference schedule"
                f"<br><sup style='color:{MUTED_TEXT}'>"
                "Each cell is a scheduled presentation (labelled by id) — hover for "
                "full details"
                "</sup>"
            ),
            x=0.02,
            xanchor="left",
        ),
        xaxis=dict(
            title="Chair (room)",
            side="top",
            showgrid=False,
            linecolor=AXIS_COLOR,
            tickfont=dict(color=MUTED_TEXT),
        ),
        yaxis=dict(
            title="Day · session start time",
            autorange="reversed",
            showgrid=False,
            linecolor=AXIS_COLOR,
            tickfont=dict(color=MUTED_TEXT),
        ),
        plot_bgcolor=SURFACE_COLOR,
        paper_bgcolor=SURFACE_COLOR,
        font=dict(family=FONT_FAMILY, color=PRIMARY_TEXT),
        margin=dict(l=160, r=40, t=100, b=20),
        height=max(400, 26 * len(slot_labels) + 160),
        width=max(520, 140 * len(chair_order) + 200),
    )

    return fig


DATA_COLUMN_WIDTH = 36  # openpyxl width units ~= characters of the default font
DATA_FONT_SIZE = 10
POINTS_PER_LINE = 15  # ~ one wrapped line at DATA_FONT_SIZE, including leading
ROW_PADDING_POINTS = 8


def _cell_text(info):
    return (
        f"ID: {info['id']}\n"
        f"Participants: {info['participant_1']}, {info['participant_2']}, "
        f"{info['participant_3']}\n"
        f"Chair: {info['chair']}\n"
        f"Day {info['day']}, session {info['session']}"
    )


def _wrapped_line_count(text, column_width):
    # Estimates how many visual lines `text` wraps to at `column_width` characters
    # per line - deliberately a slight over-estimate (never under), since a row
    # that's a touch taller than it needs to be is far less broken than one that
    # clips or overlaps the row below it.
    chars_per_line = max(1, int(column_width))
    return sum(-(-len(line) // chars_per_line) for line in text.split("\n"))


def export_schedule_to_excel(schedule, presentations, session_times, path):
    """Write a solved schedule to an .xlsx file, mirroring plot_schedule's layout.

    A spreadsheet has no hover, so every occupied cell's full detail - id,
    participants, chair, day, and session - is written directly as wrapped
    text, not just a compact label. Row heights are sized per row to fit
    whichever of that row's cells wraps to the most lines, so long names
    never get clipped or bleed into the row below.
    """
    chair_order, slot_labels, cells = _build_grid(
        schedule, presentations, session_times
    )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Schedule"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor=ACCENT_COLOR.lstrip("#").upper())
    cell_fill = PatternFill("solid", fgColor=ACCENT_TINT.lstrip("#").upper())
    data_font = Font(size=DATA_FONT_SIZE)
    wrap_top = Alignment(wrap_text=True, vertical="top")

    corner = sheet.cell(row=1, column=1, value="Day · session start time")
    corner.font = header_font
    corner.fill = header_fill

    for j, chair in enumerate(chair_order, start=2):
        header_cell = sheet.cell(row=1, column=j, value=chair)
        header_cell.font = header_font
        header_cell.fill = header_fill
        header_cell.alignment = Alignment(horizontal="center", vertical="center")

    for i, label in enumerate(slot_labels, start=2):
        row_header = sheet.cell(row=i, column=1, value=label)
        row_header.font = Font(bold=True, size=DATA_FONT_SIZE)
        row_header.alignment = Alignment(vertical="top", wrap_text=True)

        max_lines = 1
        for j, info in enumerate(cells[i - 2], start=2):
            if info is None:
                continue
            text = _cell_text(info)
            excel_cell = sheet.cell(row=i, column=j, value=text)
            excel_cell.fill = cell_fill
            excel_cell.font = data_font
            excel_cell.alignment = wrap_top
            max_lines = max(max_lines, _wrapped_line_count(text, DATA_COLUMN_WIDTH))

        row_height = max_lines * POINTS_PER_LINE + ROW_PADDING_POINTS
        sheet.row_dimensions[i].height = row_height

    sheet.column_dimensions[get_column_letter(1)].width = 22
    for j in range(2, len(chair_order) + 2):
        sheet.column_dimensions[get_column_letter(j)].width = DATA_COLUMN_WIDTH

    sheet.freeze_panes = "B2"

    workbook.save(path)

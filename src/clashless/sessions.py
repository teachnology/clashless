class Sessions:
    """Wraps a mapping from presentation id to its session label.

    `source` is a `dict` `{id: session_label}`. A session identifies which
    parallel room/track a presentation belongs to - `session_label` may be
    any hashable value, and many presentations may share a label across
    different days without conflict; only a same-day, same-slot clash
    matters. This is a thin wrapper with no validation of its own -
    consistency with a `Participants` object (same id set) is checked by
    `Schedule`, since only there are both objects available together.
    """

    def __init__(self, source):
        self.data = dict(source)

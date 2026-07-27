class Participants:
    """Wraps a mapping from presentation id to its list of participants.

    `source` is a `dict` `{id: [participant, ...]}`. Every presentation must
    have at least one participant (a `ValueError` is raised on an empty
    list) and no participant may repeat within one presentation's own list
    (a `ValueError` is raised on an in-row duplicate). There is no enforced
    maximum list length. Participants are unordered and interchangeable -
    this is just "who is involved," nothing more (no chair or other
    distinguished role).
    """

    def __init__(self, source):
        data = {}
        for presentation_id, source_people in source.items():
            people = list(source_people)
            if not people:
                raise ValueError(
                    f"Presentation {presentation_id!r} has no participants."
                )
            if len(set(people)) != len(people):
                raise ValueError(
                    f"Presentation {presentation_id!r} has a duplicate participant."
                )
            data[presentation_id] = people

        self.data = data

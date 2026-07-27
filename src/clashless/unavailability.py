class Unavailability:
    """Wrap per-person unavailability rules and answer is_unavailable queries.

    `source` is a `dict` `{person: [(day, slot), ...]}`. `None` is the
    wildcard marker for a rule element:
      - (None, slot)  -> unavailable at that slot, every day
      - (day, None)   -> unavailable the whole day
      - (day, slot)   -> unavailable for that specific slot only
      - (None, None)  -> unavailable for the entire conference

    A person may have any number of rules; all apply.
    """

    def __init__(self, source):
        self.data = {person: list(rules) for person, rules in source.items()}

    def is_unavailable(self, person, day, slot):
        """Return whether `person` is unavailable at (day, slot)."""
        for rule_day, rule_slot in self.data.get(person, []):
            day_matches = rule_day is None or rule_day == day
            slot_matches = rule_slot is None or rule_slot == slot
            if day_matches and slot_matches:
                return True
        return False
